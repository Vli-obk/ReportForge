import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Section(str, Enum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    NOTES = "notes"
    OTHER = "other"


_INCOME_KEYWORDS: List[str] = [
    r"\brevenue\b", r"net\s+revenue", r"total\s+revenue", r"net\s+sales",
    r"gross\s+profit", r"gross\s+margin",
    r"operating\s+(income|profit|loss)",
    r"net\s+(income|loss|earnings)",
    r"\bebitda\b", r"\bebit\b",
    r"earnings?\s+per\s+share", r"\beps\b",
    r"cost\s+of\s+(goods\s+sold|revenue|sales)", r"\bcogs\b",
    r"sg&a", r"selling.*general.*administrative",
    r"income\s+from\s+operations",
    r"income\s+statement",
    r"statement\s+of\s+(operations|income|earnings)",
    r"consolidated\s+statements?\s+of\s+(income|operations|earnings)",
]

_BALANCE_KEYWORDS: List[str] = [
    r"total\s+assets",
    r"total\s+liabilities",
    r"shareholders['\s]*equity", r"stockholders['\s]*equity",
    r"retained\s+earnings",
    r"current\s+assets", r"non.?current\s+assets",
    r"current\s+liabilities", r"non.?current\s+liabilities",
    r"long.?term\s+debt", r"short.?term\s+(debt|borrowings)",
    r"accounts\s+(receivable|payable)",
    r"cash\s+and\s+(cash\s+)?equivalents",
    r"\binventories?\b",
    r"\bgoodwill\b", r"intangible\s+assets",
    r"balance\s+sheet",
    r"consolidated\s+balance\s+sheets?",
    r"statement\s+of\s+financial\s+position",
]

_CASHFLOW_KEYWORDS: List[str] = [
    r"operating\s+activities",
    r"investing\s+activities",
    r"financing\s+activities",
    r"capital\s+expenditures?", r"\bcapex\b",
    r"free\s+cash\s+flow",
    r"net\s+cash",
    r"depreciation\s+and\s+amortization", r"\bd&a\b",
    r"cash\s+flows?",
    r"statement\s+of\s+cash\s+flows?",
    r"consolidated\s+statements?\s+of\s+cash\s+flows?",
]

_NOTES_KEYWORDS: List[str] = [
    r"\bnote\s+\d+",
    r"\bfootnote\b",
    r"accounting\s+policies",
    r"significant\s+accounting",
    r"basis\s+of\s+presentation",
    r"use\s+of\s+estimates",
    r"recently\s+adopted",
    r"fair\s+value\s+measurement",
]


@dataclass
class ChunkClassification:
    section: Section
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)


class SectionClassifier:
    """
    Fast, zero-cost, keyword-based section classifier.
    Assigns each text chunk to the most likely financial statement section.
    """

    def __init__(self) -> None:
        self._patterns: dict = {
            Section.INCOME_STATEMENT: self._compile(_INCOME_KEYWORDS),
            Section.BALANCE_SHEET: self._compile(_BALANCE_KEYWORDS),
            Section.CASH_FLOW: self._compile(_CASHFLOW_KEYWORDS),
            Section.NOTES: self._compile(_NOTES_KEYWORDS),
        }

    @staticmethod
    def _compile(keywords: List[str]) -> List[re.Pattern]:
        return [re.compile(kw, re.IGNORECASE) for kw in keywords]

    def classify(self, text: str) -> ChunkClassification:
        scores: dict = {}
        matched: dict = {}

        for section, patterns in self._patterns.items():
            hits = [pat.pattern for pat in patterns if pat.search(text)]
            scores[section] = len(hits)
            matched[section] = hits

        best = max(scores, key=lambda s: scores[s])
        best_score = scores[best]

        if best_score == 0:
            return ChunkClassification(Section.OTHER, 0.0)

        total = sum(scores.values()) or 1
        confidence = min(best_score / total + best_score * 0.03, 1.0)
        return ChunkClassification(
            section=best,
            confidence=round(confidence, 3),
            matched_keywords=matched[best],
        )

    def classify_chunks(self, chunks: List[str]) -> List[Tuple[str, ChunkClassification]]:
        return [(chunk, self.classify(chunk)) for chunk in chunks]

    @staticmethod
    def is_relevant(cls: ChunkClassification) -> bool:
        return cls.section in (
            Section.INCOME_STATEMENT,
            Section.BALANCE_SHEET,
            Section.CASH_FLOW,
        )
