import re
from datetime import datetime

import pandas as pd

from txn_pipeline.extractors.base import (
    END_OF_ROW,
    END_OF_ROW_TOKEN,
    PageType,
    construct_extract_transactions,
)


def parse_table_d(tabletext: str) -> pd.DataFrame:
    mode = "payments"

    # Split the input text into lines - these can be treated as input into a state machine
    lines = tabletext.splitlines()

    transactions = []
    initial_state = "transaction_date"

    buffer = {}
    state = initial_state

    # Skip the header lines
    lines = lines[5:]
    # Sometimes there is an additional header line
    # This indicates we are parsing a charges and credits table
    if lines[0] == "Spend Categories":
        mode = "charges_and_credits"
        lines = lines[3:]
    else:
        lines.pop(0)

    # State machine like processing
    while lines:
        match state:
            case "transaction_date":
                buffer["transaction_date"] = lines.pop(0)
                state = "posting_date"
            case "posting_date":
                line = lines.pop(0)
                buffer["posting_date"] = line[0:6]

                # Occassionally, the description starts on this line
                remaining_line = line[6:]
                if remaining_line:
                    # Remove the first character since it is a space after the date
                    lines.insert(0, remaining_line[1:])

                state = "description"
            case "description":
                if mode == "payments":
                    # All Payment transactions only have a one line description
                    # There seems to be a variable amount of spaces in the description - clean it up
                    buffer["description"] = " ".join(lines.pop(0).split())
                    state = "amount"
                if mode == "charges_and_credits":
                    # Charge descriptions can be multiline so we're not sure when it ends until the next line is a number (the amount)
                    if re.match(r"^-?[\d,]*\.\d\d$", lines[1]):
                        state = "category"
                        continue
                    # There seems to be a variable amount of spaces in the description - clean it up
                    if "description" not in buffer:
                        buffer["description"] = " ".join(lines.pop(0).split())
                        # It can sometime start with "Q " or "Ý ", so we need to remove this
                        buffer["description"] = buffer["description"].removeprefix("Q ")
                        buffer["description"] = buffer["description"].removeprefix("Ý ")
                    else:
                        buffer["description"] += " " + " ".join(lines.pop(0).split())
            case "category":
                buffer["category"] = lines.pop(0)
                state = "amount"
            case "amount":
                if mode == "payments":
                    buffer["amount"] = "-" + lines.pop(0)
                else:
                    buffer["amount"] = lines.pop(0)
                state = END_OF_ROW
                # Need a placeholder token to process the end of the row
                lines.insert(0, END_OF_ROW_TOKEN)
            case _ if state == END_OF_ROW:
                transactions.append(buffer.copy())
                buffer = {}
                state = initial_state
                lines.pop(0)

    return pd.DataFrame(transactions)


def process_transactions_d(
    transactions: pd.DataFrame,
    statement_date: datetime,
) -> pd.DataFrame:
    transactions["description"] = transactions["description"]
    transactions["amount"] = transactions["amount"].str.replace(",", "")

    # Determine the year from the statement date
    transactions["transaction_date_year"] = statement_date.year
    if statement_date.month == 1:
        transactions.loc[
            transactions["transaction_date"].apply(lambda x: "Dec" in x),
            "transaction_date_year",
        ] -= 1

    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"]
        + " "
        + transactions["transaction_date_year"].astype(str),
        format="%b %d %Y",
    )
    return transactions


extract_transactions_d = construct_extract_transactions(
    page_type_regexes={
        "Your account at a glance": PageType.SUMMARY,
        "Trans\ndate\nPost\ndate\nDescription\n": PageType.TRANSACTIONS,
    },
    statement_date_regex="Statement Date\n(.*)\n",
    statement_date_format="%B %d, %Y",
    table_regex=r"(Trans\ndate\n[\s\S]*?\.\d\d\n)(?=Total|If you find an error or irregularity)",
    parse_table=parse_table_d,
    process_transactions=process_transactions_d,
)
