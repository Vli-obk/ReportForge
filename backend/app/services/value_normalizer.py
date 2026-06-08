import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MULTIPLIERS = {
    "trillion": 1_000_000_000_000,
    "billion": 1_000_000_000,
    "million": 1_000_000,
    "thousand": 1_000,
    "t": 1_000_000_000_000,
    "b": 1_000_000_000,
    "m": 1_000_000,
    "k": 1_000,
}

# Matches optional paren-negative, optional sign, optional currency, number, optional multiplier
_VALUE_RE = re.compile(
    r"""
    (?P<open_paren>\()?             # opening paren → negative
    (?P<sign>-\s*)?                 # leading minus
    [$€£¥₹]?\s*                     # currency symbol
    (?P<int>[\d,]+)                 # integer digits (may have commas)
    (?:[.,](?P<dec>\d+))?           # decimal separator + decimals
    \s*
    (?P<mult>trillion|billion|million|thousand|[tbmk])?  # suffix multiplier
    (?P<close_paren>\))?            # closing paren → negative
    """,
    re.IGNORECASE | re.VERBOSE,
)

_NULL_VALUES = frozenset(
    {"", "n/a", "na", "nil", "null", "none", "-", "—", "–", "nm",
     "not meaningful", "not applicable", "not available", "—", "n.a."}
)

_FINANCIAL_FIELDS = frozenset({
    "revenue", "gross_profit", "operating_income", "net_income", "ebitda",
    "total_assets", "total_liabilities", "shareholders_equity",
    "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
})


class ValueNormalizer:
    """
    Converts financial string values to plain floats (in base monetary units).

    Examples:
        "$1.2B"       → 1_200_000_000.0
        "1.2 billion" → 1_200_000_000.0
        "1,200M"      → 1_200_000_000.0
        "(500)"       → -500.0
        "N/A"         → None
    """

    def normalize(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if text.lower() in _NULL_VALUES:
            return None

        result = self._parse(text)
        if result is None:
            logger.debug("value_normalizer_unparseable", extra={"raw": text[:80]})
        return result

    def normalize_dict(self, data: dict) -> dict:
        out = dict(data)
        for field in _FINANCIAL_FIELDS:
            if field in out:
                out[field] = self.normalize(out[field])
        return out

    def _parse(self, text: str) -> Optional[float]:
        m = _VALUE_RE.search(text)
        if not m:
            return None

        try:
            int_str = m.group("int").replace(",", "")
            dec_str = m.group("dec") or ""
            number = float(int_str + ("." + dec_str if dec_str else ""))
        except (ValueError, AttributeError):
            return None

        mult_key = (m.group("mult") or "").lower()
        number *= _MULTIPLIERS.get(mult_key, 1)

        negative = bool(m.group("open_paren") and m.group("close_paren")) or bool(
            m.group("sign")
        )
        if negative:
            number = -number

        return number
