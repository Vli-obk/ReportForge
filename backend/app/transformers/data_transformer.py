import csv
import json
import math
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def clean_nan(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if obj in ("nan", "NaN"):
        return None
    return obj


class DataTransformer:
    def clean_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()

        # NLP preprocessing: clean, type-infer, normalize values
        try:
            from app.services.nlp_preprocessor import preprocess_rows
            data, _ = preprocess_rows(data)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("nlp_preprocess_skipped", extra={"error": str(exc)})

        df = pd.DataFrame(data)

        # Normalise empty-looking values to NaN
        _EMPTY = {"", "null", "none", "n/a", "na", "-", "—", "nan"}
        for col in df.select_dtypes(include=["object"]):
            df[col] = df[col].map(
                lambda v: None if (isinstance(v, str) and v.strip().lower() in _EMPTY) else v
            )

        # Drop rows that are entirely null
        df = df.dropna(how="all")

        # For narrow tables (≤20 cols), drop rows with only 1 non-null value (e.g. country-only)
        # Wide tables naturally have sparse rows — don't apply this filter
        if 3 < len(df.columns) <= 20:
            df = df.dropna(thresh=2)

        # Drop columns that are entirely null
        df = df.dropna(axis=1, how="all")

        # Drop columns where >75% of values are null (keep if at least 25% filled)
        if len(df) > 0:
            min_non_null = max(1, int(len(df) * 0.25))
            df = df.dropna(axis=1, thresh=min_non_null)

        # Drop duplicate rows
        df = df.drop_duplicates()

        return df

    def clean_header(self, value: Any) -> str:
        raw = str(value or "").strip()
        if len(raw) > 3 and (len(re.findall(r"[^a-zA-Z0-9]", raw)) / len(raw) > 0.5):
            return ""
        text = re.sub(r"\s+", " ", raw).lower()
        text = re.sub(r"[^a-z0-9_]", "", text.replace(" ", "_")).strip("_")
        text = re.sub(r"\s+", "_", text)
        if not text or text in {"none", "nan", "unnamed"}:
            return ""
        if len(text) > 2 and text == text[::-1]:
            return ""
        return text[:50]

    def validate_dataset(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            raise ValueError("Malformed dataset: no usable rows extracted")
        columns = sorted({key for row in rows for key in row.keys() if key})
        if len(columns) < 1:
            raise ValueError("Insufficient structure: no usable columns")

        # Column-name quality checks — detect malformed header extraction
        import re as _re
        _year_pattern = _re.compile(r'^\d{4}(_\d{4}){1,}')   # "2025_2026_2026_..."
        _pure_number  = _re.compile(r'^\d+$')                  # "1990", "2026"
        _footnote_num = _re.compile(r'^\d+[a-z]')              # "1includesself", "3full"

        year_concat = sum(1 for c in columns if _year_pattern.match(c))
        pure_numeric = sum(1 for c in columns if _pure_number.match(c))
        footnote_col = sum(1 for c in columns if _footnote_num.match(c))
        bad_cols = year_concat + pure_numeric + footnote_col

        if len(columns) >= 3 and bad_cols / len(columns) > 0.4:
            raise ValueError(
                f"Column names look malformed ({bad_cols}/{len(columns)} are numeric/footnote-style) "
                "— likely a mis-parsed statistical table"
            )

        # Single-row datasets from large tables are almost always extraction failures
        if len(rows) == 1 and len(columns) > 8:
            raise ValueError(
                f"Single-row dataset with {len(columns)} columns — likely a mis-parsed table header row"
            )

        null_cells = 0
        total_cells = 0
        for row in rows:
            for column in columns:
                total_cells += 1
                val = row.get(column)
                if val is None or val == "" or str(val).lower() == "nan":
                    null_cells += 1
        if total_cells and (null_cells / total_cells) > 0.9:
            raise ValueError("Quality check failed: >90% empty cells detected")

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("[^a-z0-9_]", "", regex=True)
        )
        return df

    def sanitize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(c)[:50].strip().lower().replace(" ", "_") for c in df.columns]
        return df

    def standardize_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        schema: Dict[str, str] = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            if "int" in dtype:
                schema[col] = "integer"
            elif "float" in dtype:
                schema[col] = "float"
            elif "datetime" in dtype:
                schema[col] = "datetime"
            else:
                schema[col] = "string"
        return schema

    def transform_to_dataset_format(
        self,
        data: List[Dict[str, Any]],
        pdf_document_id: int,
        extraction_method: str = "pdfplumber",
    ) -> List[Dict[str, Any]]:
        """Transform raw dicts to dataset row format. Does NOT validate quality; callers validate."""
        cleaned_data = self.clean_data(data)

        cleaned_data.columns = [
            self.clean_header(c) or f"column_{i + 1}"
            for i, c in enumerate(cleaned_data.columns)
        ]

        if cleaned_data.columns.duplicated().any():
            merged: Dict[str, pd.Series] = {}
            for column in dict.fromkeys(cleaned_data.columns):
                matching = cleaned_data.loc[:, cleaned_data.columns == column]
                matching = matching.replace(
                    {"nan": np.nan, "NaN": np.nan, "None": np.nan, "": np.nan}
                )
                merged[column] = matching.bfill(axis=1).iloc[:, 0]
            cleaned_data = pd.DataFrame(merged)

        cols: List[str] = []
        seen: Dict[str, int] = {}
        for c in cleaned_data.columns:
            if c in seen:
                seen[c] += 1
                cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                cols.append(c)
        cleaned_data.columns = cols

        rows: List[Dict[str, Any]] = []
        for _, row in cleaned_data.iterrows():
            row_data: Dict[str, Any] = {}
            for k, v in row.items():
                if isinstance(v, str):
                    v = v.replace("\n", " ").strip()
                row_data[k] = v
            row_data = clean_nan(row_data)
            if all(v is None or v == "" for v in row_data.values()):
                continue
            rows.append(
                {
                    "row_data": row_data,
                    "extraction_method": extraction_method,
                    "confidence_score": 0,  # caller overrides with actual data-density score
                }
            )

        return rows

    def export_to_csv(self, df: pd.DataFrame, output_path: str) -> str:
        df.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
        return output_path

    def export_to_json(self, df: pd.DataFrame, output_path: str) -> str:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                clean_nan(df.to_dict(orient="records")), handle, ensure_ascii=False, indent=2
            )
        return output_path

    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "null_counts": df.isnull().sum().to_dict(),
            "dtypes": df.dtypes.astype(str).to_dict(),
        }
