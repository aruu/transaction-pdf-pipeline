from collections.abc import Callable

import pandas as pd

from txn_pipeline.extractors.extractor_c import extract_transactions_c
from txn_pipeline.extractors.extractor_d import extract_transactions_d

EXTRACTOR_REGISTRY: dict[str, Callable[[list[str]], pd.DataFrame]] = {
    # "ExtractorA": ExtractorA,
    # "ExtractorB": ExtractorB,
    "C": extract_transactions_c,
    "D": extract_transactions_d,
    # "ExtractorE": ExtractorE,
}
