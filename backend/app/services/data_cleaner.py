import math
import re
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Strings that mean "no value" in extracted PDF/Gemini data
_NULL_STRINGS = {"", "nan", "none", "n/a", "na", "null", "-", "--", "N/A", "NA", "NULL"}


def clean_extracted_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Clean a list of row-dicts before passing to the transformer.
    Steps (in order):
      1. Trim whitespace on all string values
      2. Normalise null-like strings → None
      3. Remove completely empty rows
      4. Remove header-repeat rows (values that echo column names)
      5. Remove rows where >75% of values are null
      6. Convert obvious numeric / date strings to native types
      7. Deduplicate (order-preserving)
    """
    if not raw_data:
        return []

    original = len(raw_data)

    data = [_trim_row(row) for row in raw_data]
    data = [_nullify_row(row) for row in data]

    data = [row for row in data if not _is_empty_row(row)]
    after_empty = len(data)

    if data:
        col_names = {str(k).lower().strip() for k in data[0]}
        data = [row for row in data if not _is_header_row(row, col_names)]
    after_headers = len(data)

    data = [row for row in data if not _is_sparse_row(row)]
    after_sparse = len(data)

    data = [_convert_types(row) for row in data]

    data = _deduplicate(data)
    final = len(data)

    removed = original - final
    if removed:
        logger.info(
            "data_cleaner removed %d of %d rows "
            "(empty=%d header_repeats=%d sparse=%d duplicates=%d)",
            removed, original,
            original - after_empty,
            after_empty - after_headers,
            after_headers - after_sparse,
            after_sparse - final,
        )

    return data


# ── per-row helpers ──────────────────────────────────────────────────────────

def _trim_row(row: Dict) -> Dict:
    return {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}


def _nullify_row(row: Dict) -> Dict:
    return {
        k: (None if isinstance(v, str) and v.strip().lower() in {s.lower() for s in _NULL_STRINGS} else v)
        for k, v in row.items()
    }


def _is_empty_row(row: Dict) -> bool:
    for v in row.values():
        if v is None:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        return False
    return True


def _is_header_row(row: Dict, col_names: set) -> bool:
    """Return True when ≥50% of non-null values match column names (header repeated as data)."""
    vals = [str(v).lower().strip() for v in row.values() if v is not None]
    if not vals:
        return False
    matches = sum(1 for v in vals if v in col_names)
    return matches >= max(1, len(vals) * 0.5)


def _is_sparse_row(row: Dict, threshold: float = 0.75) -> bool:
    """Return True when more than `threshold` fraction of values are null."""
    if not row:
        return True
    null_count = sum(
        1 for v in row.values()
        if v is None or (isinstance(v, float) and math.isnan(v))
    )
    return null_count / len(row) > threshold


def _convert_types(row: Dict) -> Dict:
    return {k: _convert_value(v) for k, v in row.items()}


def _convert_value(v: Any) -> Any:
    if v is None or not isinstance(v, str):
        return v
    val = v.strip()
    if not val:
        return None

    # integer
    try:
        return int(val)
    except ValueError:
        pass

    # float (accept comma as decimal separator)
    try:
        return float(val.replace(",", "."))
    except ValueError:
        pass

    # common date formats → ISO string
    for pattern, fmt in (
        (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
        (r"^\d{2}/\d{2}/\d{4}$", "%d/%m/%Y"),
        (r"^\d{2}-\d{2}-\d{4}$", "%d-%m-%Y"),
    ):
        if re.match(pattern, val):
            try:
                return datetime.strptime(val, fmt).date().isoformat()
            except ValueError:
                pass

    return val


def _deduplicate(data: List[Dict]) -> List[Dict]:
    seen: set = set()
    result: List[Dict] = []
    for row in data:
        key = tuple(sorted((k, str(v)) for k, v in row.items()))
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result
