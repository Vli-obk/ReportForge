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

        df = pd.DataFrame(data)
        df = df.dropna(how="all")
        df = df.drop_duplicates()

        for col in df.select_dtypes(include=["object"]):
            df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)

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
                    "confidence_score": None,
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
