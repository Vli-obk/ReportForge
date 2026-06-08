import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FISCAL_YEAR_RE = re.compile(
    r"(fy\s*)?(20\d{2}|19\d{2})"
    r"|(q[1-4]\s*(fy\s*)?(20\d{2}|19\d{2}))"
    r"|(20\d{2}\s*[-/]\s*(q[1-4]|h[12]))",
    re.IGNORECASE,
)


@dataclass
class QualityResult:
    is_valid: bool = True
    anomalies: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

    def add_anomaly(self, msg: str) -> None:
        self.anomalies.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        self.confidence_score = max(0.0, self.confidence_score - 0.1)


class DataQualityChecker:
    """
    Validates extracted financial metrics for correctness.
    Catches hallucinations, impossible values, and missing required fields.
    """

    def check(self, metrics: Dict[str, Any]) -> QualityResult:
        result = QualityResult()

        self._required_fields(metrics, result)
        self._fiscal_year_format(metrics, result)
        self._revenue_sanity(metrics, result)
        self._balance_sheet_equation(metrics, result)
        self._margin_sanity(metrics, result)
        self._asset_sign(metrics, result)

        logger.info(
            "data_quality_check",
            extra={
                "company": metrics.get("company_name"),
                "fiscal_year": metrics.get("fiscal_year"),
                "valid": result.is_valid,
                "anomalies": len(result.anomalies),
                "confidence": result.confidence_score,
            },
        )
        return result

    # ------------------------------------------------------------------ #

    def _required_fields(self, m: dict, r: QualityResult) -> None:
        for fld in ("company_name", "fiscal_year"):
            val = m.get(fld)
            if not val or str(val).strip().lower() in ("", "null", "none", "n/a"):
                r.add_anomaly(f"Missing required field: {fld}")

    def _fiscal_year_format(self, m: dict, r: QualityResult) -> None:
        fy = str(m.get("fiscal_year", ""))
        if fy and not _FISCAL_YEAR_RE.search(fy):
            r.add_warning(f"Unusual fiscal_year format: {fy!r}")

    def _revenue_sanity(self, m: dict, r: QualityResult) -> None:
        rev = m.get("revenue")
        if rev is None:
            return
        if rev < 0:
            r.add_anomaly(f"Revenue is negative ({rev}): likely extraction error")
        elif 0 < rev < 1_000:
            r.add_warning(
                f"Revenue is very small ({rev}): verify units are in base currency"
            )

    def _balance_sheet_equation(self, m: dict, r: QualityResult) -> None:
        assets = m.get("total_assets")
        liab = m.get("total_liabilities")
        equity = m.get("shareholders_equity")

        if assets and liab and equity and assets > 0:
            implied = assets - liab
            deviation = abs(implied - equity) / assets
            if deviation > 0.20:
                r.add_warning(
                    f"Balance sheet mismatch: assets={assets:.0f}, "
                    f"liabilities={liab:.0f}, equity={equity:.0f} "
                    f"(implied equity={implied:.0f}, deviation={deviation:.1%})"
                )

    def _margin_sanity(self, m: dict, r: QualityResult) -> None:
        rev = m.get("revenue")
        ni = m.get("net_income")
        if rev and ni and rev > 0:
            margin = ni / rev
            if margin > 1.0:
                r.add_anomaly(
                    f"Net income margin > 100% ({margin:.1%}): likely unit mismatch"
                )
            elif margin < -3.0:
                r.add_warning(f"Extreme net loss margin ({margin:.1%})")

    def _asset_sign(self, m: dict, r: QualityResult) -> None:
        assets = m.get("total_assets")
        if assets is not None and assets < 0:
            r.add_anomaly(f"Total assets is negative ({assets}): impossible value")
