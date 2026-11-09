import inspect

from txn_pipeline.extractors.extractor_c import extract_transactions_c


def test_base():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Jan. 1 Jan. 1 
                    Example Merchant
                    1.99 
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Example Merchant,1.99
    """)


def test_extra_header():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Card number: XXXX XXXX XXXX
                    Jan. 1 Jan. 1 
                    Example Merchant
                    1.99 
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Example Merchant,1.99
    """)


def test_posting_date_new_line():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Jan. 1
                    Jan. 1 
                    Example Merchant
                    1.99 
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Example Merchant,1.99
    """)


def test_multiline_messy_spacing_description():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Jan. 1 Jan. 1 
                    Example       Merchant
                    on 
                    multiple 
                    lines
                    1.99 
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Example Merchant on multiple lines,1.99
    """)


def test_value_no_space():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Jan. 1 Jan. 1 
                    Example Merchant
                    1.99
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Example Merchant,1.99
    """)


def test_credit():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Jan. 1 Jan. 1 
                    Cashback
                    100.00\u00a0CR
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2024-01-01,Cashback,-100.00
    """)


def test_previous_year_transaction():
    assert extract_transactions_c(
        list(
            {
                "0": inspect.cleandoc("""
                    Summary of your account
                    Statement date
                    Jan. 15, 2024
                    Page 1 of 3
                """),
                "1": inspect.cleandoc("""
                    Page 2 of 3
                """),
                "2": inspect.cleandoc("""
                    Transactions since your last statement
                    TRANS
                    DATE
                    POSTING
                    DATE
                    DESCRIPTION
                    AMOUNT ($)
                    Dec. 31 Dec. 31 
                    Example Merchant
                    1.99
                    Subtotal for CARD
                    Page 3 of 3
                """),
            }.values()
        )
    ).to_csv(index=False).strip() == inspect.cleandoc("""
        transaction_date,description,amount
        2023-12-31,Example Merchant,1.99
    """)
