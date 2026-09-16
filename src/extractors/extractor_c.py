import re
from datetime import datetime

import pandas as pd

from extractors.base import (
    END_OF_ROW,
    END_OF_ROW_TOKEN,
    PageType,
    construct_extract_transactions,
)


def parse_table_c(tabletext: str) -> pd.DataFrame:
    # Split the input text into lines - these can be treated as input into a state machine
    lines = tabletext.splitlines()

    transactions = []
    initial_state = "transaction_date"

    buffer = {}
    state = initial_state

    # Skip the header lines
    lines = lines[6:]

    # Sometimes there is an additional header line that we need to skip
    if re.match(r"^Card number: XXXX XXXX XXXX", lines[0]):
        lines.pop(0)

    # State machine like processing
    while lines:
        match state:
            case "transaction_date":
                line = lines.pop(0)
                parts = line.split()
                # The posting date could be on the same line - if so, push it back onto the stack
                if len(parts) == 4:
                    lines.insert(0, parts[2] + " " + parts[3])
                buffer["transaction_date"] = parts[0] + " " + parts[1]
                state = "posting_date"
            case "posting_date":
                line = lines.pop(0)
                parts = line.split()
                buffer["posting_date"] = parts[0] + " " + parts[1]
                state = "description"
            case "description":
                # The description can be multi-line so we're not actually sure when it ends, until we reach the amount
                if re.match(r"^[\d,]*\.\d\d ?(\xa0CR)?$", lines[0]):
                    state = "amount"
                    continue
                # There seems to be a variable amount of spaces in the description - clean it up
                if "description" not in buffer:
                    buffer["description"] = " ".join(lines.pop(0).split())
                else:
                    buffer["description"] += " " + " ".join(lines.pop(0).split())
            case "amount":
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


def process_transactions_c(
    transactions: pd.DataFrame,
    statement_date: datetime,
) -> pd.DataFrame:
    return transactions.rename(
        columns={
            "amount": "amount_raw",
            "transaction_date": "transaction_date_raw",
        }
    ).assign(
        # normalize the serialized amount, stripping separators and marking CR (credit) entries as negative
        amount=lambda df: (
            df["amount_raw"]
            .str.replace(",", "")
            .apply(
                lambda x: (
                    "-" + x.replace("\xa0CR", "").strip()
                    if "\xa0CR" in x
                    else x.strip()
                )
            )
        ),
        # January statements can include December transactions from the previous year
        transaction_year=lambda df: df["transaction_date_raw"].map(
            lambda x: (
                statement_date.year - 1
                if statement_date.month == 1 and "Dec." in str(x)
                else statement_date.year
            )
        ),
        # build a single datetime column using the inferred transaction year
        transaction_date=lambda df: pd.to_datetime(
            df["transaction_date_raw"] + ", " + df["transaction_year"].astype(str),
            format="%b. %d, %Y",
        ),
    )


extract_transactions_c = construct_extract_transactions(
    page_type_regexes={
        "Summary of your account": PageType.SUMMARY,
        "Transactions since your last statement": PageType.TRANSACTIONS,
    },
    statement_date_regex="Statement date\n(.*)\n",
    statement_date_format="%b. %d, %Y",
    table_regex=r"(TRANS\nDATE\n(?s:.)*?)(?:\(continued on next page\)|Subtotal for )",
    parse_table=parse_table_c,
    process_transactions=process_transactions_c,
)
