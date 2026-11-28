import inspect

import pytest

from txn_pipeline.extractors.extractor_d import extract_transactions_d


def make_pages(
    statement_date: str,
    payments_body: str,
    charges_body: str,
    charges_page_2_body: str,
) -> list[str]:
    pages = [
        inspect.cleandoc("""
            Your account at a glance
            Statement Date
            {statement_date}
            Page 1 of n
        """).format(statement_date=statement_date)
    ]
    transactions = ""
    if payments_body:
        transactions += inspect.cleandoc("""
            Your payments
            Trans
            date
            Post
            date
            Description
            Amount($)
            {payments_body}
            Total payments
            $0.00
        """).format(payments_body=payments_body)
    if charges_body:
        transactions += inspect.cleandoc("""
            Your new charges and credits
            Trans
            date
            Post
            date
            Description
            Spend Categories
            Amount($)
            Card number XXXX XXXX XXXX XXXX
            {charges_body}
        """).format(charges_body=charges_body)
        if charges_page_2_body:
            transactions += "\nIf you find an error or irregularity"
        else:
            transactions += "\nTotal for XXXX XXXX XXXX XXXX\n$0.00"
    pages.append(transactions)
    if charges_page_2_body:
        pages.append(
            inspect.cleandoc("""
                Your new charges and credits (continued)
                Trans
                date
                Post
                date
                Description
                Spend Categories
                Amount($)
                Card number XXXX XXXX XXXX XXXX
                {charges_page_2_body}
                Total for XXXX XXXX XXXX XXXX
                $0.00
            """).format(charges_page_2_body=charges_page_2_body)
        )
    return pages


@pytest.mark.parametrize(
    (
        "statement_date, "
        "payments_body, "
        "charges_body, "
        "charges_page_2_body, "
        "expected_output"
    ),
    [
        pytest.param(
            "January 15, 2024",
            "Jan 01\nJan 01\nPAYMENT THANK YOU/PAIEMENT MERCI\n100.00",
            "Jan 01\nJan 01\nMerchant\nCategory\n1.99",
            "",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,PAYMENT THANK YOU/PAIEMENT MERCI,-100.00\n"
                "2024-01-01,Merchant,1.99\n"
            ),
            id="base-case",
        ),
        pytest.param(
            "January 15, 2024",
            "Jan 01\nJan 01\nPAYMENT THANK YOU/PAIEMENT MERCI\n100.00",
            "",
            "",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,PAYMENT THANK YOU/PAIEMENT MERCI,-100.00\n"
            ),
            id="payments-only",
        ),
        pytest.param(
            "January 15, 2024",
            "",
            "Jan 01\nJan 01\nMerchant\nCategory\n1.99",
            "",
            "transaction_date,description,amount\n2024-01-01,Merchant,1.99\n",
            id="charges-only",
        ),
        pytest.param(
            "January 15, 2024",
            "",
            "Jan 01\nJan 01\nReimbursement\nCategory\n-1.99",
            "",
            "transaction_date,description,amount\n2024-01-01,Reimbursement,-1.99\n",
            id="credit-transactions",
        ),
        pytest.param(
            "January 15, 2024",
            "Jan 01\nJan 01\nPAYMENT THANK YOU/PAIEMENT MERCI\n100.00",
            "Jan 01\nJan 01\nMerchant\nCategory\n1.99",
            "Jan 02\nJan 02\nMerchant2\nCategory\n2.99",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,PAYMENT THANK YOU/PAIEMENT MERCI,-100.00\n"
                "2024-01-01,Merchant,1.99\n"
                "2024-01-02,Merchant2,2.99\n"
            ),
            id="two-pages",
        ),
        pytest.param(
            "January 15, 2024",
            "",
            "Jan 01\nJan 01\nMerchant\nCategory\n1.99",
            "Jan 02\nJan 02\nMerchant2\nCategory\n2.99",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,Merchant,1.99\n"
                "2024-01-02,Merchant2,2.99\n"
            ),
            id="two-pages-charges-only",
        ),
        pytest.param(
            "January 15, 2024",
            "Dec 30\nDec 30\nPAYMENT THANK YOU/PAIEMENT MERCI\n100.00",
            "Dec 31\nDec 31\nMerchant\nCategory\n1.99",
            "",
            (
                "transaction_date,description,amount\n"
                "2023-12-30,PAYMENT THANK YOU/PAIEMENT MERCI,-100.00\n"
                "2023-12-31,Merchant,1.99\n"
            ),
            id="previous-year-transactions",
        ),
        pytest.param(
            "January 15, 2024",
            "Jan 01\nJan 01\nPAYMENT       THANK YOU/PAIEMENT           MERCI\n100.00",
            "Jan 01\nJan 01\nMercha     nt\nCategory\n1.99",
            "Jan 02\nJan 02\nMerc   hant  2 NAME\nCategory\n2.99",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,PAYMENT THANK YOU/PAIEMENT MERCI,-100.00\n"
                "2024-01-01,Mercha nt,1.99\n"
                "2024-01-02,Merc hant 2 NAME,2.99\n"
            ),
            id="extra-spaces",
        ),
        pytest.param(
            "January 15, 2024",
            "",
            (
                "Jan 01\n"
                "Jan 01\n"
                "Website\n"
                "12.95  USD @ 1.404633205**\n"
                "Foreign Currency Transactions\n"
                "18.19\n"
                "Jan 02\n"
                "Jan 02\n"
                "Merchant\n"
                "Category\n"
                "1.99"
            ),
            "",
            (
                "transaction_date,description,amount\n"
                "2024-01-01,Website 12.95 USD @ 1.404633205**,18.19\n"
                "2024-01-02,Merchant,1.99\n"
            ),
            id="multiline-description",
        ),
        pytest.param(
            "January 15, 2024",
            "",
            "Jan 01\nJan 01 Q Merchant\nCategory\n1.99",
            "",
            "transaction_date,description,amount\n2024-01-01,Merchant,1.99\n",
            id="q-symbol-description-inline-with-posting-date",
        ),
    ],
)
def test_extract_transactions_d(
    statement_date: str,
    payments_body: str,
    charges_body: str,
    charges_page_2_body: str,
    expected_output: str,
):
    assert (
        extract_transactions_d(
            make_pages(
                statement_date,
                payments_body,
                charges_body,
                charges_page_2_body,
            )
        ).to_csv(index=False)
        == expected_output
    )
