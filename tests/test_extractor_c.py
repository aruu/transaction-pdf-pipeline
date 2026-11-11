import inspect

import pytest

from txn_pipeline.extractors.extractor_c import extract_transactions_c


def make_pages(statement_date: str, transactions_body: str) -> list[str]:
    return [
        inspect.cleandoc("""
            Summary of your account
            Statement date
            {statement_date}
            Page 1 of 3
        """).format(statement_date=statement_date),
        inspect.cleandoc("""
            Page 2 of 3
        """),
        inspect.cleandoc("""
            Transactions since your last statement
            TRANS
            DATE
            POSTING
            DATE
            DESCRIPTION
            AMOUNT ($)
            {transactions_body}
            Subtotal for CARD
            Page 3 of 3
        """).format(transactions_body=transactions_body),
    ]


def make_output(output_body: str) -> str:
    return inspect.cleandoc("""
        transaction_date,description,amount
        {output_body}
    """).format(output_body=output_body)


@pytest.mark.parametrize(
    "statement_date, transactions_body, output_body",
    [
        pytest.param(
            "Jan. 15, 2024",
            "Jan. 1 Jan. 1 \nExample Merchant Name Description\n1.99 ",
            "2024-01-01,Example Merchant Name Description,1.99",
            id="single-transaction",
        ),
        pytest.param(
            "Jan. 15, 2024",
            (
                "Card number: XXXX XXXX XXXX\n"
                "Jan. 1 Jan. 1 \n"
                "Example Merchant Name Description\n"
                "1.99 "
            ),
            "2024-01-01,Example Merchant Name Description,1.99",
            id="extra-header-line",
        ),
        pytest.param(
            "Jan. 15, 2024",
            "Jan. 1\nJan. 1 \nExample Merchant Name Description\n1.99 ",
            "2024-01-01,Example Merchant Name Description,1.99",
            id="posting-date-separate-line",
        ),
        pytest.param(
            "Jan. 15, 2024",
            "Jan. 1 Jan. 1 \nExample       Merchant \nName \n    Description\n1.99 ",
            "2024-01-01,Example Merchant Name Description,1.99",
            id="multiline-messy-spacing-description",
        ),
        pytest.param(
            "Jan. 15, 2024",
            "Jan. 1 Jan. 1 \nExample Merchant Name Description\n1.99",
            "2024-01-01,Example Merchant Name Description,1.99",
            id="amount-without-trailing-space",
        ),
        pytest.param(
            "Jan. 15, 2024",
            (
                "Jan. 1 Jan. 1 \nExample Merchant Name Description\n1.99\n"
                "Jan. 2 Jan. 2 \nCashback\n100.00\u00a0CR"
            ),
            (
                "2024-01-01,Example Merchant Name Description,1.99\n"
                "2024-01-02,Cashback,-100.00"
            ),
            id="credit",
        ),
        pytest.param(
            "Jan. 15, 2024",
            "Dec. 31 Dec. 31 \nExample Merchant Name Description\n1.99",
            "2023-12-31,Example Merchant Name Description,1.99",
            id="previous-year-transaction",
        ),
    ],
)
def test_extract_transactions_c(
    statement_date: str,
    transactions_body: str,
    output_body: str,
):
    assert extract_transactions_c(make_pages(statement_date, transactions_body)).to_csv(
        index=False
    ).strip() == make_output(output_body)
