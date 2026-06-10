import re
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_DATE = re.compile(
    r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'
    r'|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}'
    r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}'
    r'|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}'
    r'|\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}'
    r')\b',
    re.IGNORECASE,
)

_AMOUNT = re.compile(
    r'(?:[$€£¥₹]\s*[\d\s,]+(?:[.,]\d{1,2})?'
    r'|[\d\s,]+(?:[.,]\d{1,2})?\s*(?:[$€£¥₹]|USD|EUR|GBP|MAD|DZD|DA|DH))'
    r'(?:\s*(?:HT|TTC|TVA|VAT))?',
    re.IGNORECASE,
)

_KV_LINE = re.compile(
    r'^([\w][\w\s\-/()àâäéèêëîïôùûüç]{1,45})\s*[:\-]\s*(.{1,200})$',
    re.IGNORECASE | re.MULTILINE,
)

_INVOICE_KEYWORDS = re.compile(
    r'\b(invoice|facture|bon de commande|purchase order|devis|receipt|reçu|bill)\b',
    re.IGNORECASE,
)
_FINANCIAL_KEYWORDS = re.compile(
    r'\b(revenue|chiffre d.affaires|net income|bénéfice|profit|loss|perte'
    r'|balance sheet|bilan|cash flow|trésorerie|ebitda|actif|passif)\b',
    re.IGNORECASE,
)
_CONTRACT_KEYWORDS = re.compile(
    r'\b(contract|contrat|agreement|accord|clause|partie|signataire|whereas)\b',
    re.IGNORECASE,
)

# Looks like a text table: 3+ whitespace-separated columns on most lines
_TABLE_LINE = re.compile(r'^.{4,}\s{2,}.{2,}\s{2,}.{2,}$')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LocalExtractorService:

    def extract(self, text: str, filename: str = "") -> List[Dict[str, Any]]:
        """Return a list of row dicts extracted from text without any external API."""
        if not text or not text.strip():
            return []

        doc_type = self._detect_type(text, filename)

        rows: List[Dict[str, Any]] = []

        if doc_type == "invoice":
            rows = self._extract_invoice(text)
        elif doc_type == "financial":
            rows = self._extract_financial(text)
        elif doc_type == "contract":
            rows = self._extract_contract(text)

        # Supplement with text-table rows regardless of doc type
        table_rows = self._extract_text_table(text)
        if table_rows and len(table_rows) > len(rows):
            rows = table_rows

        # Final fallback: generic key-value pairs
        if not rows:
            rows = self._extract_kv(text)

        return rows

    # -----------------------------------------------------------------------
    # Type detection
    # -----------------------------------------------------------------------

    def _detect_type(self, text: str, filename: str) -> str:
        sample = (filename + " " + text[:3000]).lower()
        if _INVOICE_KEYWORDS.search(sample):
            return "invoice"
        if _FINANCIAL_KEYWORDS.search(sample):
            return "financial"
        if _CONTRACT_KEYWORDS.search(sample):
            return "contract"
        return "generic"

    # -----------------------------------------------------------------------
    # Invoice extraction
    # -----------------------------------------------------------------------

    def _extract_invoice(self, text: str) -> List[Dict[str, Any]]:
        meta = self._extract_kv(text)
        header = meta[0] if meta else {}

        # Look for line-item table (item / qty / price pattern)
        items = self._extract_line_items(text)
        if items:
            for item in items:
                item.update({k: v for k, v in header.items() if k not in item})
            return items

        return meta if meta else []

    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract invoice line items heuristically."""
        lines = text.splitlines()
        items: List[Dict[str, Any]] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            amounts = _AMOUNT.findall(line)
            if not amounts:
                continue
            # Strip amounts to get description
            desc = _AMOUNT.sub("", line).strip(" \t|,;:")
            desc = re.sub(r'\s+', ' ', desc).strip()
            if len(desc) < 3:
                continue
            row: Dict[str, Any] = {"description": desc}
            if amounts:
                row["amount"] = amounts[-1].strip()
            if len(amounts) >= 2:
                row["unit_price"] = amounts[0].strip()
            dates = _DATE.findall(line)
            if dates:
                row["date"] = dates[0]
            items.append(row)

        return items

    # -----------------------------------------------------------------------
    # Financial extraction
    # -----------------------------------------------------------------------

    _FIN_LABELS = [
        ("revenue",          re.compile(r'(?:total\s+)?(?:net\s+)?(?:revenue|sales|chiffre\s+d.affaires)', re.I)),
        ("gross_profit",     re.compile(r'gross\s+(?:profit|margin)|marge\s+brute', re.I)),
        ("operating_income", re.compile(r'operating\s+(?:income|profit)|résultat\s+(?:d.exploitation|opérationnel)', re.I)),
        ("net_income",       re.compile(r'net\s+(?:income|profit|earnings|loss)|bénéfice\s+net|résultat\s+net', re.I)),
        ("ebitda",           re.compile(r'ebitda|excédent\s+brut', re.I)),
        ("total_assets",     re.compile(r'total\s+assets?|total\s+actif', re.I)),
        ("total_liabilities",re.compile(r'total\s+liabilit|total\s+passif', re.I)),
        ("equity",           re.compile(r"(?:shareholders?|stockholders?|owners?)['\s]*equity|capitaux\s+propres", re.I)),
        ("operating_cashflow", re.compile(r'(?:net\s+)?cash\s+(?:from|provided\s+by)\s+operat', re.I)),
    ]

    def _extract_financial(self, text: str) -> List[Dict[str, Any]]:
        row: Dict[str, Any] = {}
        lines = text.splitlines()

        for line in lines:
            for field, pat in self._FIN_LABELS:
                if field in row:
                    continue
                if pat.search(line):
                    amounts = _AMOUNT.findall(line)
                    if amounts:
                        row[field] = amounts[-1].strip()

        dates = _DATE.findall(text[:2000])
        if dates:
            row["period"] = dates[0]

        # company name: first non-empty line that's not a pure number/date
        for line in text.splitlines()[:10]:
            line = line.strip()
            if len(line) > 4 and not re.match(r'^[\d\W]+$', line):
                row["company"] = line[:120]
                break

        return [row] if row else self._extract_kv(text)

    # -----------------------------------------------------------------------
    # Contract extraction
    # -----------------------------------------------------------------------

    def _extract_contract(self, text: str) -> List[Dict[str, Any]]:
        kv = self._extract_kv(text)
        clauses = self._extract_clauses(text)
        if clauses and len(clauses) > len(kv):
            return clauses
        return kv if kv else clauses

    def _extract_clauses(self, text: str) -> List[Dict[str, Any]]:
        clause_pat = re.compile(
            r'^(?:Article|Clause|Section|§)\s*(\d+[\.\d]*)\s*[:\-–]?\s*(.{0,120})',
            re.IGNORECASE | re.MULTILINE,
        )
        rows = []
        for m in clause_pat.finditer(text):
            rows.append({"clause": m.group(1).strip(), "title": m.group(2).strip()})
        return rows

    # -----------------------------------------------------------------------
    # Text-table extraction (whitespace-aligned columns)
    # -----------------------------------------------------------------------

    def _extract_text_table(self, text: str) -> List[Dict[str, Any]]:
        lines = [l for l in text.splitlines() if _TABLE_LINE.match(l)]
        if len(lines) < 3:
            return []

        # Split by 2+ spaces to get columns
        split_lines = [re.split(r'\s{2,}', l.strip()) for l in lines]
        col_counts = [len(r) for r in split_lines]
        if not col_counts:
            return []

        # Find most common column count
        from collections import Counter
        common_count = Counter(col_counts).most_common(1)[0][0]
        split_lines = [r for r in split_lines if len(r) == common_count]
        if len(split_lines) < 2:
            return []

        headers = [f"col_{i+1}" for i in range(common_count)]
        # Use first row as headers only if: no amount cells AND cells look like
        # short labels (≤6 words, ≤50 chars) — prevents document sentences becoming column names
        first = split_lines[0]
        _STOP = re.compile(r'\b(of|the|and|for|from|with|by|as|at|in|on|to)\b', re.I)
        def _cell_is_label(c: str) -> bool:
            c = c.strip()
            words = c.split()
            if len(words) > 3 or len(c) > 50:
                return False
            if len(words) == 3 and _STOP.search(c):
                return False
            # Reject pure-numeric cells — years (1990, 2026) and page numbers are not headers
            if re.match(r'^\d+$', c):
                return False
            # Reject cells that are mostly digits (e.g. "2025u", "2026p")
            if len(c) <= 6 and sum(ch.isdigit() for ch in c) / max(len(c), 1) >= 0.6:
                return False
            return True
        first_has_amounts = any(_AMOUNT.search(cell) for cell in first)
        first_looks_like_labels = all(_cell_is_label(cell) for cell in first)
        if not first_has_amounts and first_looks_like_labels:
            headers = [re.sub(r'\s+', '_', h.lower().strip()[:40]) or f"col_{i+1}" for i, h in enumerate(first)]
            split_lines = split_lines[1:]

        rows = []
        for cells in split_lines:
            row = {headers[i]: cells[i].strip() for i in range(min(len(headers), len(cells)))}
            if any(v for v in row.values()):
                rows.append(row)

        return rows

    # -----------------------------------------------------------------------
    # Generic key-value extraction
    # -----------------------------------------------------------------------

    def _extract_kv(self, text: str) -> List[Dict[str, Any]]:
        row: Dict[str, Any] = {}
        for m in _KV_LINE.finditer(text):
            key = re.sub(r'\s+', '_', m.group(1).strip().lower())
            key = re.sub(r'[^a-z0-9_àâäéèêëîïôùûüç]', '', key)[:50]
            value = m.group(2).strip()
            if not key or not value or value.lower() in ('n/a', '-', '—', 'none', ''):
                continue
            row[key] = value
        return [row] if row else []
