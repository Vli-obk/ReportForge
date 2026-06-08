"""
Unit tests for the financial report extraction pipeline.
No database or Gemini API required — all components are tested in isolation.
"""
import pytest
from app.services.value_normalizer import ValueNormalizer
from app.services.section_classifier import Section, SectionClassifier
from app.services.data_quality import DataQualityChecker
from app.services.text_cleaner import TextCleaner


# ────────────────────────────────────────────────────────────────────────────
# ValueNormalizer
# ────────────────────────────────────────────────────────────────────────────

class TestValueNormalizer:
    def setup_method(self):
        self.n = ValueNormalizer()

    def test_billion_symbol(self):
        assert self.n.normalize("$1.2B") == pytest.approx(1_200_000_000.0)

    def test_billion_word(self):
        assert self.n.normalize("1.2 billion") == pytest.approx(1_200_000_000.0)

    def test_million_with_commas(self):
        assert self.n.normalize("1,200M") == pytest.approx(1_200_000_000.0)

    def test_million_word(self):
        assert self.n.normalize("1,200 million") == pytest.approx(1_200_000_000.0)

    def test_thousand(self):
        assert self.n.normalize("500K") == pytest.approx(500_000.0)

    def test_parentheses_negative(self):
        assert self.n.normalize("(1,500)") == pytest.approx(-1_500.0)

    def test_negative_billion(self):
        assert self.n.normalize("-2.5B") == pytest.approx(-2_500_000_000.0)

    def test_plain_integer(self):
        assert self.n.normalize("123456") == pytest.approx(123_456.0)

    def test_comma_separated(self):
        assert self.n.normalize("1,234,567") == pytest.approx(1_234_567.0)

    def test_null_string(self):
        assert self.n.normalize("N/A") is None

    def test_dash(self):
        assert self.n.normalize("—") is None

    def test_nil(self):
        assert self.n.normalize("nil") is None

    def test_none_value(self):
        assert self.n.normalize(None) is None

    def test_int_passthrough(self):
        assert self.n.normalize(42) == pytest.approx(42.0)

    def test_float_passthrough(self):
        assert self.n.normalize(3.14) == pytest.approx(3.14)

    def test_trillion(self):
        assert self.n.normalize("1T") == pytest.approx(1_000_000_000_000.0)

    def test_normalize_dict_only_touches_financial_fields(self):
        data = {
            "company_name": "Acme",
            "revenue": "$500M",
            "fiscal_year": "FY2024",
            "net_income": "(25M)",
        }
        out = self.n.normalize_dict(data)
        assert out["company_name"] == "Acme"        # untouched
        assert out["fiscal_year"] == "FY2024"        # untouched
        assert out["revenue"] == pytest.approx(500_000_000.0)
        assert out["net_income"] == pytest.approx(-25_000_000.0)

    def test_currency_euro(self):
        assert self.n.normalize("€2.5B") == pytest.approx(2_500_000_000.0)


# ────────────────────────────────────────────────────────────────────────────
# SectionClassifier
# ────────────────────────────────────────────────────────────────────────────

class TestSectionClassifier:
    def setup_method(self):
        self.c = SectionClassifier()

    def test_income_statement(self):
        text = "Revenue: $10B\nNet income: $1.2B\nEBITDA: $2B"
        result = self.c.classify(text)
        assert result.section == Section.INCOME_STATEMENT
        assert result.confidence > 0.3

    def test_balance_sheet(self):
        text = "Total assets: 500B\nTotal liabilities: 300B\nShareholders equity: 200B"
        result = self.c.classify(text)
        assert result.section == Section.BALANCE_SHEET

    def test_cash_flow(self):
        text = "Cash flows from operating activities\nNet cash from investing activities"
        result = self.c.classify(text)
        assert result.section == Section.CASH_FLOW

    def test_notes(self):
        text = "Note 1: Significant accounting policies\nNote 2: Basis of presentation"
        result = self.c.classify(text)
        assert result.section == Section.NOTES

    def test_other(self):
        text = "This is the CEO letter to shareholders about our strategy."
        result = self.c.classify(text)
        assert result.section == Section.OTHER

    def test_is_relevant_income(self):
        text = "Net income: $1.2B\nRevenue: $10B"
        assert SectionClassifier.is_relevant(self.c.classify(text))

    def test_is_relevant_other(self):
        text = "CEO message: we had a great year."
        assert not SectionClassifier.is_relevant(self.c.classify(text))

    def test_classify_chunks(self):
        chunks = [
            "Revenue $10B, Net income $1B",
            "Total assets $50B, Total liabilities $30B",
            "Annual general meeting notice",
        ]
        results = self.c.classify_chunks(chunks)
        assert len(results) == 3
        assert results[0][1].section == Section.INCOME_STATEMENT
        assert results[1][1].section == Section.BALANCE_SHEET


# ────────────────────────────────────────────────────────────────────────────
# DataQualityChecker
# ────────────────────────────────────────────────────────────────────────────

class TestDataQualityChecker:
    def setup_method(self):
        self.q = DataQualityChecker()

    def _good(self, **overrides):
        base = {
            "company_name": "Acme Corp",
            "fiscal_year": "FY2024",
            "currency": "USD",
            "revenue": 10_000_000_000.0,
            "net_income": 1_200_000_000.0,
            "total_assets": 50_000_000_000.0,
            "total_liabilities": 30_000_000_000.0,
            "shareholders_equity": 20_000_000_000.0,
        }
        base.update(overrides)
        return base

    def test_valid_report(self):
        result = self.q.check(self._good())
        assert result.is_valid

    def test_missing_company_name(self):
        result = self.q.check(self._good(company_name=None))
        assert not result.is_valid
        assert any("company_name" in a for a in result.anomalies)

    def test_missing_fiscal_year(self):
        result = self.q.check(self._good(fiscal_year=None))
        assert not result.is_valid

    def test_negative_revenue(self):
        result = self.q.check(self._good(revenue=-100_000_000.0))
        assert not result.is_valid
        assert any("negative" in a.lower() for a in result.anomalies)

    def test_negative_assets(self):
        result = self.q.check(self._good(total_assets=-1.0))
        assert not result.is_valid

    def test_impossible_margin(self):
        result = self.q.check(self._good(revenue=100.0, net_income=500.0))
        assert not result.is_valid
        assert any("margin" in a.lower() for a in result.anomalies)

    def test_balance_sheet_mismatch_warning(self):
        result = self.q.check(
            self._good(
                total_assets=100_000.0,
                total_liabilities=60_000.0,
                shareholders_equity=1_000.0,  # should be ~40k
            )
        )
        assert any("mismatch" in w.lower() for w in result.warnings)

    def test_confidence_starts_at_one(self):
        result = self.q.check(self._good())
        assert result.confidence_score == pytest.approx(1.0)

    def test_warnings_reduce_confidence(self):
        result = self.q.check(
            self._good(
                total_assets=100_000.0,
                total_liabilities=60_000.0,
                shareholders_equity=1_000.0,
            )
        )
        assert result.confidence_score < 1.0


# ────────────────────────────────────────────────────────────────────────────
# TextCleaner
# ────────────────────────────────────────────────────────────────────────────

class TestTextCleaner:
    def setup_method(self):
        self.c = TextCleaner(min_page_repeats=2)

    def test_removes_page_numbers(self):
        pages = {1: "Revenue: $10B\n\n42\n\nNet income: $1B"}
        result = self.c.clean_pages(pages)
        assert "42" not in result.text
        assert "Revenue" in result.text

    def test_removes_repeated_headers(self):
        header = "ACME CORP — ANNUAL REPORT 2024"
        pages = {
            1: f"{header}\n\nRevenue: $10B",
            2: f"{header}\n\nNet income: $1B",
            3: f"{header}\n\nTotal assets: $50B",
        }
        result = self.c.clean_pages(pages)
        # Header should be removed (appears on all 3 pages)
        assert result.text.count(header) == 0

    def test_removes_toc(self):
        toc_page = (
            "Table of Contents\n"
            "Financial Highlights ..................... 5\n"
            "Income Statement ........................ 10\n"
            "Balance Sheet .......................... 15\n"
        )
        financial_page = "Revenue: $10B\nNet income: $1B"
        pages = {1: toc_page, 2: financial_page}
        result = self.c.clean_pages(pages)
        assert "Revenue" in result.text
        # TOC entries should be stripped
        assert "Financial Highlights" not in result.text

    def test_deduplicates_identical_pages(self):
        # Pages 2 and 3 are identical; page 1 has unique financial content.
        # min_page_repeats=2 → lines appearing on 2+ pages are stripped as
        # repeated headers. Pages 2 and 3 share the same content so those lines
        # are removed, leaving only the unique content from page 1.
        unique = "Revenue: $10B\nNet income: $1B"
        repeated_text = "Boilerplate footer line"
        pages = {1: unique, 2: repeated_text, 3: repeated_text}
        result = self.c.clean_pages(pages)
        assert "Revenue" in result.text
        # Boilerplate that appears on 2+ pages should be removed
        assert repeated_text not in result.text

    def test_empty_input(self):
        result = self.c.clean_pages({})
        assert result.text == ""
        assert result.source_pages == []

    def test_preserves_financial_content(self):
        pages = {
            1: (
                "CONSOLIDATED STATEMENTS OF INCOME\n"
                "Revenue: $10,500,000,000\n"
                "Gross profit: $4,200,000,000\n"
                "Net income: $1,200,000,000\n"
            )
        }
        result = self.c.clean_pages(pages)
        assert "Revenue" in result.text
        assert "10,500,000,000" in result.text
