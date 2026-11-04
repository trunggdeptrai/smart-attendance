from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


def records_to_dataframe(
    records: Sequence[Mapping[str, Any]] | None,
    columns: Sequence[str],
) -> pd.DataFrame:
    """Build a DataFrame with a stable schema, including when there are no rows."""
    column_names = list(columns)
    if records is None:
        rows = []
    elif isinstance(records, Mapping):
        rows = [records]
    else:
        rows = records
    return pd.DataFrame.from_records(rows, columns=column_names)
