"""
Extract transactions from the text of pages.

The extractor is responsible for extracting the fields (transaction_date, description, amount),
and then ensuring that the data is in chronologically ascending order.
"""

import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from enum import Enum

import pandas as pd

# Constants for transaction table processing
END_OF_ROW = "end_of_row"
END_OF_ROW_TOKEN = "EOR"


class PageType(Enum):
    SUMMARY = "summary"
    TRANSACTIONS = "transactions"
    OTHER = "other"


def classify_pages(
    pages: list[str],
    page_type_regexes: dict[str, PageType],
) -> dict[PageType, list[str]]:
    """
    Classify pages based on the provided regex patterns.

    This method iterates through the pages and assigns a PageType
    based on the first matching regex pattern.

    Args:
        pages (list[str]): List of pages as text.
        page_type_regexes (dict[str, PageType]): Dictionary of regex patterns for classifying pages.

    Returns:
        dict[PageType, list[str]]: A dictionary where keys are page types and values
        are the pages belonging to that type.
    """

    classified_pages: dict[PageType, list[str]] = defaultdict(list)

    # Iterate through pages, assign to first matching type or OTHER
    for page in pages:
        classification = PageType.OTHER
        for regex, page_type in page_type_regexes.items():
            if re.search(regex, page):
                classification = page_type
                break
        classified_pages[classification].append(page)

    return dict(classified_pages)  # convert back to a regular dict


def extract_statement_date(
    summary_page: str,
    statement_date_regex: str,
    statement_date_format: str,
) -> datetime:
    """Extract the statement date from the summary page.

    Args:
        summary_page (str): The text content of the summary page.

    Returns:
        datetime: The statement date as a datetime object
    """
    statement_date_str = re.findall(statement_date_regex, summary_page)[0]
    return datetime.strptime(statement_date_str, statement_date_format)  # noqa: DTZ007


def extract_raw_transactions(
    pages: list[str],
    table_regex: str,
    parse_table: Callable[[str], pd.DataFrame],
) -> pd.DataFrame:

    transaction_tables = []
    # loop through all transaction pages
    for page in pages:
        # extract transaction tables (there may be multiple)
        tables = re.findall(table_regex, page)
        for table in tables:
            # parse each one into a DataFrame
            transaction_tables.append(parse_table(table))
    transactions_all = pd.concat(transaction_tables)

    return transactions_all


def construct_extract_transactions(
    page_type_regexes: dict[str, PageType],
    statement_date_regex: str,
    statement_date_format: str,
    table_regex: str,
    parse_table: Callable[[str], pd.DataFrame],
    process_transactions: Callable[
        [pd.DataFrame, datetime], pd.DataFrame
    ] = lambda df, _: df,
) -> Callable[[list[str]], pd.DataFrame]:
    """Construct a transaction extractor configured for a particular statement format.

    The returned function classifies pages, extracts and parses transaction
    tables, applies account-specific transaction processing, and returns the
    transactions sorted by date.

    Args:
        page_type_regexes (dict[str, PageType]): Dictionary of regex patterns for classifying pages.
        statement_date_regex (str): Regex pattern for extracting the statement date.
        statement_date_format (str): Format for parsing the statement date.
        table_regex (str): Regex pattern for extracting table texts from a page text.
        parse_table (Callable[[str], pd.DataFrame]): Function that parses a transaction table into a DataFrame.
        process_transactions (Callable[[pd.DataFrame, datetime], pd.DataFrame]): Function that applies account-specific formatting to the parsed transactions.

    Returns:
        Callable[[list[str]], pd.DataFrame]: A function that accepts page text
        and returns a DataFrame containing transaction_date, description, and
        amount columns sorted by transaction_date.
    """

    def extract_transactions(pages: list[str]) -> pd.DataFrame:
        classified_pages = classify_pages(pages, page_type_regexes)
        statement_date = extract_statement_date(
            classified_pages[PageType.SUMMARY][0],
            statement_date_regex,
            statement_date_format,
        )
        transactions = extract_raw_transactions(
            classified_pages[PageType.TRANSACTIONS],
            table_regex,
            parse_table,
        )

        # account-specific formatting, such as:
        # - how negative values are represented
        # - whether or not a dollar sign or extra spaces are present
        # - appending the year if it is implied (with special handling for Dec/Jan)
        transactions = process_transactions(transactions, statement_date)

        # select the output columns and sort
        return (
            transactions[["transaction_date", "description", "amount"]]
            .sort_values("transaction_date", kind="stable")
            .reset_index(drop=True)
        )

    return extract_transactions
