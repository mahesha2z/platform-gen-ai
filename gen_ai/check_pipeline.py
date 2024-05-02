#!/usr/bin/env python3
"""
This module checks the efficiency of a pipeline in processing questions using a language model.
It provides functionality to load questions from a CSV file and process each question through
the model to evaluate response times and effectiveness under various scenarios. This script
supports running in batch or step mode to accommodate different testing requirements.

Classes:
    None

Functions:
    get_input_df(csv_path)
    run_single_prediction(question, member_context_full=None)
    get_default_personalized_info(row)
    run_pipeline(mode, csv_path=None)

Exceptions:
    None
"""
import uuid
from timeit import default_timer
from typing import Literal

import click
import llm
import pandas as pd

from gen_ai.common.ioc_container import Container


def get_input_df(csv_path: str) -> pd.DataFrame:
    """Loads a CSV file and returns it as a pandas DataFrame.

    Args:
        csv_path (str): The path to the CSV file to be loaded.

    Returns:
        pd.DataFrame: A DataFrame containing the data from the CSV file.
    """
    df = pd.read_csv(csv_path)
    return df


def run_single_prediction(question: str, member_context_full: dict | None = None) -> str:
    """Processes a single question through the language model API and returns the response.

    Args:
        question (str): The question to be processed by the language model.
        member_context_full (dict | None): Optional dictionary containing additional context to personalize
        the language model's response.

    Returns:
        str: The answer generated by the language model, or an error message if the process fails.

    Raises:
        Exception: An exception is raised and caught internally if the language model API call fails.
        The specific error message is printed.
    """
    try:
        conversation = llm.respond_api(question, member_context_full)
        return conversation.exchanges[-1].answer
    except Exception as e:  # pylint: disable=W0718
        Container.logger().info(msg=e)
        return "I apologize, but no answer is available at this time."


def get_default_personalized_info(row: dict) -> dict | None:
    """Extracts and returns the default personalization information from a row if available.

    Args:
        row (dict): The row from which personalization information is to be extracted.

    Returns:
        dict | None: A dictionary containing personalization information if 'set_number' exists in the row;
        otherwise, None.

    Side Effects:
        Prints a fallback message if 'set_number' is not found in the row.
    """
    if "set_number" in row:
        return {"set_number": row["set_number"].lower()}
    Container.logger().info(msg="Personalization info does not have set_number, falling back to None")
    return None


@click.command()
@click.argument("mode", required=True)
@click.argument("csv_path", required=False, type=click.Path(exists=True))
@click.argument("comments", required=False)
def run_pipeline(mode: Literal["batch", "step"] = "step", csv_path: str = None, comments: str | None = None) -> None:
    """Executes the pipeline check based on the specified mode.

    This function orchestrates the loading and processing of questions to evaluate the language model's response
    efficiency.
    In 'batch' mode, it processes questions from a CSV file; in 'step' mode, it runs a set of predefined questions
    to measure performance iteratively.

    Args:
        mode (Literal["batch", "step"]): The mode of operation. 'batch' processes questions from a CSV file,
                                         'step' processes a predefined list of questions.
        csv_path (str, optional): The path to the CSV file containing questions. Required if mode is 'batch'.

    Raises:
        ValueError: If the specified mode is not implemented.

    Side Effects:
        Prints session details, questions, and responses to the console.
        Measures and displays execution time in 'step' mode.
    """
    session_id = str(uuid.uuid4())
    Container.session_id = session_id
    Container.logger().info(msg=f"Session id is: {session_id}")
    Container.comments = comments
    if mode == "batch":

        df = get_input_df(csv_path)
        for i, row in df.iterrows():
            Container.logger().info(msg=f"Asking question {i} in document ")
            question = row["question"]
            Container.logger().info(msg=f"Question: {question}")

            if Container.config.get("personalization"):
                personalized_data = get_default_personalized_info(row)
            answer = run_single_prediction(question, personalized_data)
            Container.logger().info(msg=f"Answer: {answer}")
    elif mode == "step":
        start = default_timer()
        for idx, input_query in enumerate(["What has EQT management said about optimal capital structure"]):
            Container.logger().info(msg=f"Asking question {idx} in document ")
            Container.logger().info(msg=f"Question: {input_query}")
            answer = run_single_prediction(input_query, {"set_number": ""})
            Container.logger().info(msg=f"Answer: {answer}")
        end = default_timer()
        print(f"Total flow took {end - start} seconds")
    else:
        raise ValueError("Not implemented mode")


if __name__ == "__main__":
    run_pipeline()
