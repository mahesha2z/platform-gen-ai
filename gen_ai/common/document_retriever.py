"""Provides classes for retrieving documents based on semantic analysis.

This module contains the `DocumentRetrieverProvider` for selecting the appropriate document
retriever based on a given criterion (e.g., semantic analysis) and the abstract base class
`DocumentRetriever` alongside its implementation, `SemanticDocumentRetriever`.

The `SemanticDocumentRetriever` is designed to retrieve related documents from a `Chroma`
vector store based on semantic similarity to a provided query, potentially filtered by
additional metadata criteria. It leverages similarity search and max marginal relevance
techniques to find and rank documents according to their relevance.
"""

import copy
from abc import ABC, abstractmethod
from typing import Any

from langchain_community.vectorstores.chroma import Chroma
from langchain_core.documents.base import Document

import gen_ai.common.common as common
from gen_ai.common.argo_logger import trace_on
from gen_ai.common.chroma_utils import convert_to_chroma_format


def remove_member_id(metadata: dict[str, Any]) -> dict[str, Any]:
    """Removes the "member_id" key from a metadata dictionary.

    This function creates a copy of the input dictionary, deletes the "member_id" key from
    the copy, and returns the modified copy.

    Args:
        metadata (dict): The input metadata dictionary.

    Returns:
        dict: A new dictionary with the "member_id" key removed.
    """
    new_metadata = copy.deepcopy(metadata)
    if "member_id" in new_metadata:
        del new_metadata["member_id"]
    return new_metadata


class DocumentRetrieverProvider:
    def __call__(self, name: str) -> "DocumentRetriever":
        if name == "semantic":
            return SemanticDocumentRetriever()
        else:
            raise ValueError("Not implemented document retriver")


class DocumentRetriever(ABC):
    """
    Abstract base class for retrieving documents from a document store based on certain criteria.

    This class provides the framework for implementations that retrieve documents related to given queries.
    Subclasses must implement the `get_related_docs_from_store` method, which fetches documents based on
    semantic criteria or other specific conditions from a document store.

    Methods:
        get_related_docs_from_store(store, questions_for_search, metadata=None): Abstract method that must be
            implemented by subclasses to retrieve related documents based on the query and optional metadata.

        get_multiple_related_docs_from_store(store, questions_for_search, metadata=None): Retrieves multiple sets of
            documents for each question in a list. It aggregates results across multiple queries, removing duplicates
            and combining results from the individual document retrieval calls.

    Usage:
        Subclasses should provide specific implementations for fetching documents based on the criteria defined
        in `get_related_docs_from_store`. The `get_multiple_related_docs_from_store` method can be used directly
        by instances of the subclasses to handle multiple queries.
    """

    @abstractmethod
    def get_related_docs_from_store(
        self, store: Chroma, questions_for_search: str, metadata: dict = None
    ) -> list[Document]:
        pass

    def get_multiple_related_docs_from_store(
        self, store: Chroma, questions_for_search: list[str], metadata: dict[str, str] | None = None
    ):
        documents = []
        for question in questions_for_search:
            documents.extend(self.get_related_docs_from_store(store, question, metadata))
        documents = common.remove_duplicates(documents)
        return documents


class SemanticDocumentRetriever(DocumentRetriever):
    """Implements document retrieval based on semantic similarity from a Chroma store.

    This retriever utilizes semantic similarity searches and max marginal relevance (MMR)
    algorithms to identify and rank documents from a Chroma vector store that are most
    relevant to a given query string. The process can be optionally refined using
    metadata filters to narrow down the search results further.

    Attributes:
        store (Chroma): The Chroma vector store instance from which documents are retrieved.
        questions_for_search (str): The query string used for finding related documents.
        metadata (dict, optional): Additional metadata for filtering the documents in the
            search query.
    """

    # @trace_on("Retrieving documents from semantic store", measure_time=True)
    # def get_related_docs_from_store(
    #     self, store: Chroma, questions_for_search: str, metadata: dict[str, str] | None = None
    # ) -> list[Document]:
    #     if metadata is None:
    #         metadata = {}
    #     metadata = remove_member_id(metadata)
    #     if metadata is not None and len(metadata) > 1:
    #         metadata = convert_to_chroma_format(metadata)

    #     ss_docs = store.similarity_search_with_score(query=questions_for_search, k=50, filter=metadata)
    #     ss_docs = [x[0] for x in ss_docs[0:3]]

    #     mmr_docs = store.max_marginal_relevance_search(
    #         query=questions_for_search, k=2, lambda_mult=0.5, filter=metadata
    #     )
    #     docs = common.remove_duplicates(ss_docs + mmr_docs)

    #     return docs
    @trace_on("Retrieving documents from semantic store", measure_time=True)
    def get_related_docs_from_store(
        self, store: Chroma, questions_for_search: str, metadata: dict[str, str] | None = None
    ) -> list[Document]:
        if metadata is None:
            metadata = {}
        metadata = remove_member_id(metadata)
        if metadata is not None and len(metadata) > 1:
            metadata = convert_to_chroma_format(metadata)

        ss_docs = store.similarity_search_with_score(query=questions_for_search, k=50)
        ss_docs = [x[0] for x in ss_docs[0:20]]

        mmr_docs = store.max_marginal_relevance_search(
            query=questions_for_search, k=1, lambda_mult=0.5
        )
        docs = common.remove_duplicates(ss_docs + mmr_docs)

        return docs
    @trace_on("Retrieving documents from semantic store", measure_time=True)
    def get_related_docs_from_store_uhg(
        self, store: Chroma, questions_for_search: str, metadata: dict[str, str] | None = None
    ) -> list[Document]:
        # Very custom method
        if metadata is None or "set_number" not in metadata:
            custom_metadata = {"data_source": "kc"}
            return self.get_related_docs_from_store(store, questions_for_search, custom_metadata)

        b360_metadata = copy.deepcopy(metadata)
        b360_metadata["data_source"] = "b360"

        kc_metadata = copy.deepcopy(metadata)
        kc_metadata["data_source"] = "kc"
        if "set_number" in kc_metadata:
            del kc_metadata["set_number"]
        metadatas = [b360_metadata, kc_metadata]
        docs = []
        for metadata in metadatas:
            docs.extend(self.get_related_docs_from_store(store, questions_for_search, metadata))

        return docs
