import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_DISCLAIMER_PATTERNS = [
    r"forward[- ]looking statements?",
    r"safe harbor",
    r"cautionary (note|statement|language)",
    r"actual results? (may|might|could) differ",
    r"risk factors?",
    r"this (annual|quarterly) report on form",
    r"non-GAAP (financial measures?|reconciliation)",
]

_TOC_PATTERNS = [
    r"^\s*table of contents?\s*$",
    r"^\s*contents?\s*$",
]

_PAGE_NUMBER_PATTERNS = [
    r"^\s*-?\s*\d{1,4}\s*-?\s*$",     # bare page numbers: "42", "-42-"
    r"page\s+\d+\s+of\s+\d+",          # "Page 3 of 42"
    r"^\s*f-\d+\s*$",                   # SEC filing style "F-3"
    r"^\s*[ivxlcdm]+\s*$",             # roman numeral page numbers
]

# TOC entry: any line that ends with dots then a page number
_TOC_ENTRY_RE = re.compile(r"^.{1,100}\.{3,}\s*\d+\s*$")


@dataclass
class CleanedDocument:
    text: str
    page_texts: Dict[int, str]
    removed_blocks: int
    source_pages: List[int]


class TextCleaner:
    """
    Removes boilerplate from financial reports:
    - Repeated headers and footers (appear on >= min_page_repeats pages)
    - Page numbers
    - Table of contents sections
    - Legal disclaimer paragraphs
    - Duplicate text blocks (hash-based)
    """

    def __init__(self, min_page_repeats: int = 3):
        self.min_page_repeats = min_page_repeats
        self._disclaimer_re = re.compile(
            "|".join(_DISCLAIMER_PATTERNS), re.IGNORECASE
        )
        self._toc_re = re.compile(
            "|".join(_TOC_PATTERNS), re.IGNORECASE | re.MULTILINE
        )
        self._page_num_re = re.compile(
            "|".join(_PAGE_NUMBER_PATTERNS), re.IGNORECASE | re.MULTILINE
        )

    def clean_pages(self, page_texts: Dict[int, str]) -> CleanedDocument:
        if not page_texts:
            return CleanedDocument("", {}, 0, [])

        repeated = self._find_repeated_lines(page_texts)
        cleaned_pages: Dict[int, str] = {}
        seen_hashes: set = set()
        removed_total = 0

        for page_num in sorted(page_texts):
            cleaned, removed = self._clean_page(
                page_texts[page_num], repeated, seen_hashes
            )
            cleaned_pages[page_num] = cleaned
            removed_total += removed

        full_text = "\n\n".join(
            cleaned_pages[p] for p in sorted(cleaned_pages) if cleaned_pages[p].strip()
        )
        source_pages = [p for p in sorted(cleaned_pages) if cleaned_pages[p].strip()]

        logger.info(
            "text_cleaner_done",
            extra={
                "pages_in": len(page_texts),
                "pages_out": len(source_pages),
                "removed_blocks": removed_total,
                "output_chars": len(full_text),
            },
        )
        return CleanedDocument(
            text=full_text,
            page_texts=cleaned_pages,
            removed_blocks=removed_total,
            source_pages=source_pages,
        )

    # ------------------------------------------------------------------ #

    def _find_repeated_lines(self, page_texts: Dict[int, str]) -> set:
        """Lines that appear on >= min_page_repeats pages are headers/footers."""
        counter: Counter = Counter()
        for text in page_texts.values():
            seen_this_page: set = set()
            for line in text.splitlines():
                s = line.strip()
                # Only short lines can be headers/footers
                if 3 <= len(s) <= 150 and s not in seen_this_page:
                    counter[s] += 1
                    seen_this_page.add(s)
        return {line for line, n in counter.items() if n >= self.min_page_repeats}

    def _clean_page(
        self, text: str, repeated: set, seen_hashes: set
    ) -> Tuple[str, int]:
        lines = text.splitlines()
        out: List[str] = []
        removed = 0
        in_toc = False

        for line in lines:
            stripped = line.strip()

            # Remove page numbers
            if self._page_num_re.match(stripped):
                removed += 1
                continue

            # Remove header/footer lines
            if stripped in repeated:
                removed += 1
                continue

            # Detect start of TOC
            if self._toc_re.match(stripped):
                in_toc = True
                removed += 1
                continue

            # Skip TOC entries (dots + page number)
            if in_toc:
                if _TOC_ENTRY_RE.match(stripped) or stripped == "":
                    removed += 1
                    continue
                else:
                    in_toc = False  # end of TOC

            out.append(line)

        cleaned = "\n".join(out)

        # Strip disclaimer paragraphs
        cleaned = self._strip_disclaimers(cleaned)

        # Duplicate-block deduplication
        block_hash = hashlib.md5(cleaned.strip().encode("utf-8", errors="replace")).hexdigest()
        if cleaned.strip() and block_hash in seen_hashes:
            return "", removed + len(out)
        if cleaned.strip():
            seen_hashes.add(block_hash)

        return cleaned, removed

    def _strip_disclaimers(self, text: str) -> str:
        """Remove short paragraphs that are pure legal boilerplate."""
        paragraphs = re.split(r"\n{2,}", text)
        kept: List[str] = []
        for para in paragraphs:
            words = para.split()
            hits = len(self._disclaimer_re.findall(para))
            # Drop if it's a short paragraph dominated by disclaimer language
            if hits >= 1 and len(words) <= 80:
                continue
            kept.append(para)
        return "\n\n".join(kept)
