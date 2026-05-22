import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import math
import re


def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if obj == "nan" or obj == "NaN":
        return None
    return obj


class DataTransformer:
    def __init__(self):
        pass

    def sanitize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(c)[:50].strip().lower().replace(' ', '_') for c in df.columns]
        return df
    
    def clean_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Clean and normalize extracted data"""
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # Remove empty rows
        df = df.dropna(how='all')
        
        # Remove duplicate rows
        df = df.drop_duplicates()
        
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).str.strip()
        
        return df
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names"""
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('[^a-z0-9_]', '', regex=True)
        return df
    
    def standardize_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        """Generate standardized schema definition"""
        schema = {}
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'int' in dtype:
                schema[col] = 'integer'
            elif 'float' in dtype:
                schema[col] = 'float'
            elif 'datetime' in dtype:
                schema[col] = 'datetime'
            else:
                schema[col] = 'string'
                
        return schema
    
    def transform_to_dataset_format(self, data: List[Dict[str, Any]], pdf_document_id: int) -> List[Dict[str, Any]]:
        cleaned_data = self.clean_data(data)

        # Sanitize column names to short readable ones
        cleaned_data.columns = [
            re.sub(r'[^a-z0-9_]', '', str(c).strip()[:40].lower().replace(' ', '_').replace('\n', '_'))
            for c in cleaned_data.columns
        ]

        # Deduplicate column names
        cols = []
        seen = {}
        for c in cleaned_data.columns:
            if c in seen:
                seen[c] += 1
                cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                cols.append(c)
        cleaned_data.columns = cols

        rows = []
        for _, row in cleaned_data.iterrows():
            row_data = {}
            for k, v in row.items():
                # Flatten multiline values
                if isinstance(v, str):
                    v = v.replace('\n', ' ').strip()
                row_data[k] = v
            row_data = clean_nan(row_data)
            # Skip completely empty rows
            if all(v is None or v == '' for v in row_data.values()):
                continue
            rows.append({
                "row_data": row_data,
                "extraction_method": "pdfplumber",
                "confidence_score": None
            })

        return rows
    
    def export_to_csv(self, df: pd.DataFrame, output_path: str) -> str:
        """Export data to CSV"""
        df.to_csv(output_path, index=False)
        return output_path
    
    def export_to_json(self, df: pd.DataFrame, output_path: str) -> str:
        """Export data to JSON"""
        df.to_json(output_path, orient='records', indent=2)
        return output_path
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics of the data"""
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "null_counts": df.isnull().sum().to_dict(),
            "dtypes": df.dtypes.astype(str).to_dict()
        }
