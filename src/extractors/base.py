"""
Extract pagetext into transactions.

The extractor is responsible for extracting fields in the format:
{account_name, file_name, transaction_date, description, amount}
and then ensuring that the data is in chronologically ascending order.
"""

import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

import pandas as pd

# Constants for page types
PAGE_TYPE_SUMMARY = "summary"
PAGE_TYPE_TRANSACTIONS = "transactions"
PAGE_TYPE_OTHER = "other"

# Constants for transaction table processing
END_OF_ROW = "end_of_row"
END_OF_ROW_TOKEN = "EOR"


def classify_pages(
    pagetexts: list[str],
    page_type_regexes: dict[str, str],
) -> dict[str, list[str]]:
    """Classify pages based on the provided regex patterns.
    This method iterates through the pagetexts and classifies each page
    into 'summary', 'transactions', or 'other' based on the regex patterns
    defined in the `page_type_regexes`.

    Args:
        pagetexts (list[str]): List of text content from PDF pages.
        page_type_regexes (dict[str, str]): Dictionary of regex patterns for classifying pages.

    Returns:
        dict[str, list[str]]: A dictionary where keys are page types and values
        are lists of pagetexts belonging to that type.
    """

    classified_pagetexts: dict[str, list[str]] = defaultdict(list)

    # Iterate through pages, assign to first matching type or OTHER
    for pagetext in pagetexts:
        classification = PAGE_TYPE_OTHER
        for regex, page_type in page_type_regexes.items():
            if re.search(regex, pagetext):
                classification = page_type
                break
        classified_pagetexts[classification].append(pagetext)

    return dict(classified_pagetexts)


def extract_statement_date(
    summary_pagetext: str,
    statement_date_regex: str,
    statement_date_format: str,
) -> datetime:
    """Extract the statement date from the summary page text.

    Args:
        summary_pagetext (str): The text content of the summary page.

    Returns:
        datetime: The parsed statement date.
    """
    statement_date_str = re.findall(statement_date_regex, summary_pagetext)[0]
    return datetime.strptime(statement_date_str, statement_date_format)  # noqa: DTZ007


def extract_raw_transactions(
    pagetexts: list[str],
    tabletext_regex: str,
    parse_transaction_table: Callable[[str], pd.DataFrame],
) -> pd.DataFrame:

    transaction_tables = []
    for pagetext in pagetexts:
        tabletexts = re.findall(tabletext_regex, pagetext)
        for tabletext in tabletexts:
            transaction_tables.append(parse_transaction_table(tabletext))

    transactions_all = pd.concat(transaction_tables)

    return transactions_all


def construct_extract_transactions(
    page_type_regexes: dict[str, str],
    statement_date_regex: str,
    statement_date_format: str,
    tabletext_regex: str,
    parse_transaction_table: Callable[[str], pd.DataFrame],
    pre_process_transactions: Callable[[pd.DataFrame, datetime], pd.DataFrame],
) -> Callable[[list[str]], pd.DataFrame]:
    """Construct a function that extracts transactions from pagetexts.

    Args:
        page_type_regexes (dict[str, str]): Dictionary of regex patterns for classifying pages.
        statement_date_regex (str): Regex pattern for extracting the statement date.
        statement_date_format (str): Format for parsing the statement date.
        tabletext_regex (str): Regex pattern for extracting table texts from a page text.
    Returns:
        callable[[list[str]], pd.DataFrame]: A function that extracts transactions from pagetexts.
    """

    def extract_transactions(pagetexts: list[str]) -> pd.DataFrame:
        # # Class variables that must be defined in subclasses
        # PAGE_TYPE_REGEXES: Mapping[str, str]
        # """Dictionary of regex patterns for classifying pages.
        # Keys are regex patterns, and values are the corresponding page types
        # (e.g., 'summary', 'transactions', 'other').
        # """
        # STATEMENT_DATE_REGEX: str
        # """Regex pattern used to extract the statement date from the summary page."""
        # STATEMENT_DATE_FORMAT: str
        # """Format string used to parse the statement date."""
        classified_pagetexts = classify_pages(pagetexts, page_type_regexes)
        statement_date = extract_statement_date(
            classified_pagetexts["summary"][0],
            statement_date_regex,
            statement_date_format,
        )
        transactions = extract_raw_transactions(
            classified_pagetexts["transactions"],
            tabletext_regex,
            parse_transaction_table,
        )
        transactions = pre_process_transactions(transactions, statement_date)

        # Select the output columns
        return (
            transactions[["transaction_date", "description", "amount"]]
            .sort_values("transaction_date", kind="stable")
            .reset_index(drop=True)
        )

    return extract_transactions
