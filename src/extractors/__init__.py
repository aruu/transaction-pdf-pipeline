from collections.abc import Callable

import pandas as pd

from extractors.extractor_c import extract_transactions_c

EXTRACTOR_REGISTRY: dict[str, Callable[[list[str]], pd.DataFrame]] = {
    # "ExtractorA": ExtractorA,
    # "ExtractorB": ExtractorB,
    "C": extract_transactions_c,
    # "ExtractorD": ExtractorD,
    # "ExtractorE": ExtractorE,
}
