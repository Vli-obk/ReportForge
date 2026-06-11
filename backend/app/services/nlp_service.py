"""
NLP Named Entity Recognition pipeline for financial, legal, and business documents.

Model stack:
  Primary  : en_core_web_sm  (English — SEC filings, annual reports, NYSE documents)
  Fallback : fr_core_news_sm (French — TotalEnergies, UNESCO, Moroccan documents)

Entity quality pipeline per page:
  1. spaCy NER  → raw entities from model
  2. Label whitelist filter  → keep only meaningful types
  3. Text quality filter     → blacklist generic document words
  4. Deduplication           → (entity_text, label, page) key
  5. Regex supplementary     → MONEY, EMAIL, PHONE, IBAN missed by NER
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Model loading ──────────────────────────────────────────────────────────────

_nlp_en = None   # en_core_web_sm
_nlp_fr = None   # fr_core_news_sm


def _get_nlp_en():
    global _nlp_en
    if _nlp_en is None:
        try:
            import spacy
            _nlp_en = spacy.load("en_core_web_sm")
            logger.info("nlp_model_loaded", extra={"model": "en_core_web_sm"})
        except Exception as exc:
            logger.warning("nlp_en_model_unavailable", extra={"error": str(exc)})
            _nlp_en = False
    return _nlp_en or None


def _get_nlp_fr():
    global _nlp_fr
    if _nlp_fr is None:
        try:
            import spacy
            _nlp_fr = spacy.load("fr_core_news_sm")
            logger.info("nlp_model_loaded", extra={"model": "fr_core_news_sm"})
        except Exception as exc:
            logger.warning("nlp_fr_model_unavailable", extra={"error": str(exc)})
            _nlp_fr = False
    return _nlp_fr or None


def _detect_language(text: str) -> str:
    """Fast heuristic: count French-specific characters/words in first 400 chars."""
    sample = text[:400].lower()
    fr_markers = len(re.findall(
        r"\b(le|la|les|des|une|pour|est|dans|avec|sur|qui|que|par|ou|et|je|nous|vous|ils|elles|être|avoir)\b",
        sample,
    ))
    en_markers = len(re.findall(
        r"\b(the|of|and|in|to|a|is|for|that|with|are|this|on|at|by|from|its|has|have|an|our|we|they)\b",
        sample,
    ))
    return "fr" if fr_markers > en_markers else "en"


# ── Label configuration ────────────────────────────────────────────────────────

# Only entity types meaningful for financial / legal / business documents.
_KEEP_LABELS_EN = frozenset({
    "ORG",      # Apple Inc., SEC, Federal Reserve
    "PERSON",   # Elon Musk, John Smith
    "GPE",      # United States, New York, California
    "LOC",      # Wall Street, Pacific Ocean
    "DATE",     # December 31 2022, Q3 2023
    "MONEY",    # $1.2 billion, €450 million
    "PERCENT",  # 14.7%, 8.3 percent
    "CARDINAL", # 7.3 million, 4,500 (counts and quantities in statistical/financial docs)
    "QUANTITY", # 3 miles, 200 kg (measurement quantities)
    "LAW",      # Securities Exchange Act, Sarbanes-Oxley
    "FAC",      # NYSE, NASDAQ
    "NORP",     # American, European, Federal
})

# French model uses different label names
_KEEP_LABELS_FR = frozenset({"PER", "ORG", "LOC", "MISC"})

# Map French labels → canonical labels used in the output schema
_FR_LABEL_MAP = {
    "PER":  "PERSON",
    "ORG":  "ORG",
    "LOC":  "LOC",
    "MISC": "MISC",
}

# Confidence baselines per label (spaCy small models expose no per-entity scores)
_LABEL_CONFIDENCE: Dict[str, float] = {
    "ORG":       0.82,
    "PERSON":    0.88,
    "GPE":       0.91,
    "LOC":       0.80,
    "DATE":      0.92,
    "MONEY":     0.94,
    "PERCENT":   0.96,
    "LAW":       0.88,
    "FAC":       0.78,
    "NORP":      0.83,
    "CARDINAL":  0.76,
    "QUANTITY":  0.80,
    "MISC":      0.68,
    # Regex-sourced labels
    "MONTANT":   0.93,
    "EMAIL":     0.99,
    "TELEPHONE": 0.91,
    "IBAN":      0.98,
}


def _confidence(label: str, entity_text: str) -> float:
    """Baseline confidence + small bonus for multi-word spans."""
    base = _LABEL_CONFIDENCE.get(label, 0.72)
    words = entity_text.split()
    # Multi-word entities are usually more precise than single tokens
    bonus = min(0.12, (len(words) - 1) * 0.02)
    return round(min(0.99, base + bonus), 2)


# ── Entity quality filters ─────────────────────────────────────────────────────

# Generic document/form words that are never real entities
_BLACKLIST: frozenset = frozenset({
    "form", "forms",
    "indicate", "indicates", "indicated", "indication",
    "management", "managers",
    "stock", "stocks",
    "item", "items",
    "part", "parts",
    "section", "sections", "subsection",
    "table", "tables",
    "page", "pages",
    "report", "reports",
    "annual", "fiscal",
    "year", "years",
    "quarter", "quarters",
    "note", "notes",
    "exhibit", "exhibits",
    "schedule", "schedules",
    "appendix",
    "index",
    "contents",
    "total", "totals", "subtotal",
    "net", "gross",
    "common", "preferred", "ordinary",
    "see", "pursuant", "herein", "thereof", "thereto", "hereof",
    "forward", "looking",
    "statement", "statements",
    "disclosure", "disclosures",
    "including", "excluding",
    "operating", "financial", "business",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "monday", "tuesday", "wednesday", "thursday", "friday",
})

# Single-word all-caps tokens that look like entity labels but are document noise
_CAPS_BLACKLIST: frozenset = frozenset({
    "FORM", "ITEM", "PART", "SECTION", "TABLE", "PAGE",
    "REPORT", "ANNUAL", "STOCK", "NOTE", "EXHIBIT",
    "MANAGEMENT", "INDICATE", "TOTAL", "NET", "GROSS",
    "COMMON", "PREFERRED", "SEE", "AND", "THE", "FOR", "NOT",
})


def _is_valid(text: str, label: str) -> bool:
    """Quality gate: return True only if this entity is worth keeping."""
    s = text.strip()

    # Must have at least 2 characters
    if len(s) < 2:
        return False

    # Must contain at least one alphabetic character
    if not any(c.isalpha() for c in s):
        return False

    lower = s.lower()

    # Generic word blacklist (case-insensitive)
    if lower in _BLACKLIST:
        return False

    words = s.split()

    # CARDINAL: must contain a digit, and single-word pure-number tokens must be ≥ 3 digits
    # (blocks bare "1", "25", etc. while keeping "7.3 million", "1,245", "2,400,000")
    if label == "CARDINAL":
        if not any(c.isdigit() for c in s):
            return False
        if len(words) == 1 and s.replace(",", "").replace(".", "").isdigit() and len(s.replace(",", "").replace(".", "")) < 3:
            return False

    # Single-word entities get extra scrutiny
    if len(words) == 1:
        # All-caps single word in caps blacklist
        if s.isupper() and s in _CAPS_BLACKLIST:
            return False
        # All-caps, very short (≤3 chars) that aren't ORG labels → noise
        if s.isupper() and len(s) <= 3 and label not in ("ORG", "GPE", "LAW"):
            return False
        # Single word ≤ 3 chars that are just letters → usually abbreviation noise
        if len(s) <= 2 and label not in ("ORG", "GPE"):
            return False

    return True


# ── Regex supplementary extractors ────────────────────────────────────────────
# Only match amounts with an explicit currency marker OR large comma-formatted numbers.
# This prevents bare years (2022) and page numbers (1, 2) from becoming MONTANT entities.

_AMOUNT_RE = re.compile(
    r"(?:€|\$|£|¥|USD|EUR|GBP|CHF|MAD|DZD|DH|DA|CAD|AUD)\s*\d[\d\s,.']*(?:[.,]\d{1,2})?"   # currency prefix
    r"|"
    r"\d[\d\s,.']*(?:[.,]\d{1,2})?\s*(?:€|\$|£|¥|USD|EUR|GBP|CHF|MAD|DZD|DH|DA|CAD|AUD)"   # currency suffix
    r"|"
    r"\d{1,3}(?:,\d{3}){2,}(?:\.\d{1,2})?",                                                   # e.g. 1,245,300,000
    re.IGNORECASE,
)

_EMAIL_RE   = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE   = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
_IBAN_RE    = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b")


def _regex_entities(text: str) -> List[Dict[str, Any]]:
    """Return supplementary entities found by regex (MONTANT, EMAIL, TELEPHONE, IBAN)."""
    found: List[Dict[str, Any]] = []

    for m in _AMOUNT_RE.finditer(text):
        val = m.group().strip()
        if len(val) >= 3:
            found.append({"text": val, "label": "MONTANT"})

    for m in _EMAIL_RE.finditer(text):
        found.append({"text": m.group(), "label": "EMAIL"})

    for m in _PHONE_RE.finditer(text):
        val = m.group().strip()
        if len(val) >= 8:
            found.append({"text": val, "label": "TELEPHONE"})

    for m in _IBAN_RE.finditer(text):
        found.append({"text": m.group(), "label": "IBAN"})

    return found


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_entities_as_rows(
    pages: List[Dict[str, Any]],
    source_document: str,
) -> List[Dict[str, Any]]:
    """
    Extract named entities page-by-page and return fixed-schema rows.
    Output schema: {entity, label, confidence, page, source_document}

    - Processes each page independently to preserve accurate page attribution.
    - Uses en_core_web_sm (English) or fr_core_news_sm (French) based on content.
    - Applies label whitelist, entity blacklist, and deduplication.
    - Supplements NER with regex for MONEY, EMAIL, PHONE, IBAN.
    """
    rows: List[Dict[str, Any]] = []
    seen: set = set()          # (normalized_text, label, page) — per-page dedup
    global_seen: set = set()   # (normalized_text, label) — cross-page dedup for exact duplicates

    stats = {"pages_processed": 0, "raw_ner": 0, "after_filter": 0, "regex_added": 0}

    for page_info in pages:
        page_num = page_info.get("page_number", 0)
        text = page_info.get("text", "")
        if not text or not text.strip():
            continue

        stats["pages_processed"] += 1
        lang = _detect_language(text)

        # ── NER extraction ──────────────────────────────────────────────────
        nlp = _get_nlp_en() if lang == "en" else (_get_nlp_fr() or _get_nlp_en())

        if nlp:
            # Process up to 100k chars per page (spaCy default max is ~1M tokens)
            doc = nlp(text[:100_000])

            for ent in doc.ents:
                stats["raw_ner"] += 1
                entity_text = ent.text.strip()
                label = ent.label_

                # Map French labels to canonical names
                if lang == "fr":
                    if label not in _KEEP_LABELS_FR:
                        continue
                    label = _FR_LABEL_MAP.get(label, label)
                else:
                    if label not in _KEEP_LABELS_EN:
                        continue

                if not _is_valid(entity_text, label):
                    continue

                stats["after_filter"] += 1
                key = (entity_text.lower(), label, page_num)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "entity": entity_text,
                    "label": label,
                    "confidence": _confidence(label, entity_text),
                    "page": page_num,
                    "source_document": source_document,
                })

        # ── Regex supplementary ─────────────────────────────────────────────
        for item in _regex_entities(text):
            entity_text = item["text"].strip()
            label = item["label"]

            key = (entity_text.lower(), label, page_num)
            if key in seen:
                continue
            seen.add(key)
            stats["regex_added"] += 1
            rows.append({
                "entity": entity_text,
                "label": label,
                "confidence": _confidence(label, entity_text),
                "page": page_num,
                "source_document": source_document,
            })

    logger.info(
        "nlp_extraction_complete",
        extra={
            "source": source_document,
            "pages_processed": stats["pages_processed"],
            "raw_ner_entities": stats["raw_ner"],
            "after_filter": stats["after_filter"],
            "regex_entities": stats["regex_added"],
            "total_rows": len(rows),
        },
    )
    return rows


def extract_entities(text: str) -> Dict[str, Any]:
    """Legacy endpoint — returns grouped entity dict for the /nlp/{id}/entities API."""
    if not text or not text.strip():
        return {"entities": {}, "total": 0}

    lang = _detect_language(text)
    nlp = _get_nlp_en() if lang == "en" else (_get_nlp_fr() or _get_nlp_en())
    result: Dict[str, List[str]] = {}

    if nlp:
        doc = nlp(text[:100_000])
        keep = _KEEP_LABELS_EN if lang == "en" else _KEEP_LABELS_FR
        for ent in doc.ents:
            label = ent.label_
            if lang == "fr":
                if label not in _KEEP_LABELS_FR:
                    continue
                label = _FR_LABEL_MAP.get(label, label)
            else:
                if label not in _KEEP_LABELS_EN:
                    continue
            value = ent.text.strip()
            if not _is_valid(value, label):
                continue
            result.setdefault(label, [])
            if value not in result[label]:
                result[label].append(value)

    for item in _regex_entities(text):
        label, value = item["label"], item["text"]
        result.setdefault(label, [])
        if value not in result[label]:
            result[label].append(value)

    for k in result:
        result[k] = result[k][:40]

    return {"entities": result, "total": sum(len(v) for v in result.values())}
