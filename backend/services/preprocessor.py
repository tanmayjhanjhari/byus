import io
import re
import zipfile
import gzip
import pandas as pd
import numpy as np

class DataPreprocessor:
    def process(self, raw_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict]:
        report = {
            "original_format": "unknown",
            "original_rows": 0,
            "final_rows": 0,
            "original_cols": 0,
            "final_cols": 0,
            "headers_added": False,
            "whitespace_cleaned": False,
            "missing_values_standardized": 0,
            "duplicates_removed": 0,
            "dtype_conversions": {},
            "columns_renamed": {},
            "uci_adult_detected": False,
            "warnings": []
        }

        # Step 1: Format Detection & Loading
        df, original_format = self._load_data(raw_bytes, filename)
        report["original_format"] = original_format
        report["original_rows"] = len(df)
        report["original_cols"] = len(df.columns)

        # Step 2: Header Detection
        df, headers_added = self._handle_headers(df)
        report["headers_added"] = headers_added

        # Step 3: Whitespace Cleaning
        df, whitespace_cleaned = self._clean_whitespace(df)
        report["whitespace_cleaned"] = whitespace_cleaned

        # Step 4: Missing Value Standardization
        df, missing_count = self._standardize_missing_values(df)
        report["missing_values_standardized"] = int(missing_count)

        # Step 5: Duplicate Row Removal
        initial_rows = len(df)
        df.drop_duplicates(inplace=True)
        report["duplicates_removed"] = int(initial_rows - len(df))

        # Step 6: Dtype Inference
        df, dtype_conversions = self._infer_dtypes(df)
        report["dtype_conversions"] = dtype_conversions

        # Step 7: Column Name Normalization
        df, renamed = self._normalize_columns(df)
        report["columns_renamed"] = renamed

        # Step 8: UCI Adult Specific Fix
        df, uci_detected = self._uci_adult_fix(df, filename)
        report["uci_adult_detected"] = uci_detected

        report["final_rows"] = len(df)
        report["final_cols"] = len(df.columns)

        return df, report

    def _load_data(self, raw_bytes: bytes, filename: str) -> tuple[pd.DataFrame, str]:
        ext = filename.lower().split('.')[-1]
        
        # Handle compressed files first
        if ext == 'zip':
            try:
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                    file_list = z.namelist()
                    if not file_list:
                        raise ValueError("ZIP archive is empty.")
                    # Pick the first file that looks like tabular data, else just first file
                    target_file = next((f for f in file_list if any(f.endswith(e) for e in ['.csv', '.tsv', '.data', '.txt'])), file_list[0])
                    raw_bytes = z.read(target_file)
                    filename = target_file
                    ext = filename.lower().split('.')[-1]
            except Exception as e:
                raise ValueError(f"Could not extract ZIP file: {str(e)}")
                
        elif ext == 'gz':
            try:
                raw_bytes = gzip.decompress(raw_bytes)
                ext = 'csv'  # Treat decompressed contents as CSV by default
            except Exception as e:
                raise ValueError(f"Could not decompress GZ file: {str(e)}")

        df = None
        fmt = ext

        try:
            if ext == 'csv':
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes))
                except Exception:
                    df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine='python')
            elif ext == 'tsv':
                df = pd.read_csv(io.BytesIO(raw_bytes), sep='\t')
            elif ext in ['xlsx', 'xls']:
                engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
                df = pd.read_excel(io.BytesIO(raw_bytes), engine=engine)
            elif ext == 'json':
                try:
                    df = pd.read_json(io.BytesIO(raw_bytes), orient='records')
                except Exception:
                    df = pd.read_json(io.BytesIO(raw_bytes), orient='columns')
            elif ext == 'parquet':
                df = pd.read_parquet(io.BytesIO(raw_bytes))
            elif ext in ['data', 'txt']:
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine='python')
                except Exception:
                    df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine='python', header=None)
            else:
                # Fallback: try reading as CSV
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine='python')
                    fmt = "csv (inferred)"
                except Exception:
                    raise ValueError(f"Unsupported or unparseable file format: {ext}")
                    
        except Exception as e:
            raise ValueError(f"Could not read file as {ext}. Please ensure it is a valid tabular file. Error: {str(e)}")
            
        if df is None or df.empty:
            raise ValueError("The parsed file contains no data.")
            
        return df, fmt

    def _handle_headers(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        # Check if all column names are integers or match Unnamed pattern
        cols = list(df.columns)
        all_numeric_or_unnamed = all(
            str(c).isdigit() or str(c).startswith("Unnamed:") 
            for c in cols
        )
        
        if all_numeric_or_unnamed:
            df.columns = [f"col_{i}" for i in range(len(cols))]
            return df, True
            
        return df, False

    def _clean_whitespace(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        cleaned = False
        # Strip whitespace from column names
        original_cols = list(df.columns)
        df.columns = [str(c).strip() for c in df.columns]
        if list(df.columns) != original_cols:
            cleaned = True

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object', 'string']).columns:
            # Using str.strip() and replacing empty strings with NaN
            s = df[col].astype(str).str.strip()
            # Restore original non-string NaNs if any
            mask = df[col].isna()
            s = s.replace('', np.nan)
            s[mask] = np.nan
            
            # Check if anything changed
            if not df[col].equals(s):
                df[col] = s
                cleaned = True
                
        return df, cleaned

    def _standardize_missing_values(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        missing_indicators = [
            '?', 'N/A', 'NA', 'n/a', 'na', 'null', 'NULL', 'None', 'none', '-', '--', 'missing', 'MISSING', 'unknown', 'Unknown'
        ]
        
        initial_nas = df.isna().sum().sum()
        df.replace(missing_indicators, np.nan, inplace=True)
        final_nas = df.isna().sum().sum()
        
        return df, final_nas - initial_nas

    def _infer_dtypes(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        conversions = {}
        for col in df.select_dtypes(include=['object', 'string']).columns:
            series = df[col]
            # Ignore completely empty columns
            if series.isna().all():
                continue
                
            numeric_series = pd.to_numeric(series, errors='coerce')
            non_null_original = series.notna().sum()
            non_null_converted = numeric_series.notna().sum()
            
            if non_null_original > 0 and (non_null_converted / non_null_original) >= 0.8:
                df[col] = numeric_series
                conversions[col] = "converted to numeric"
                
        return df, conversions

    def _normalize_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        renamed = {}
        new_cols = []
        for col in df.columns:
            new_col = str(col).lower()
            new_col = re.sub(r'[\s\-]+', '_', new_col)
            new_col = re.sub(r'[^a-z0-9_]', '', new_col)
            
            if new_col != col:
                renamed[col] = new_col
            new_cols.append(new_col)
            
        df.columns = new_cols
        return df, renamed

    def _uci_adult_fix(self, df: pd.DataFrame, filename: str) -> tuple[pd.DataFrame, bool]:
        adult_keywords = ['workclass', 'fnlwgt', 'education_num', 'marital_status', 'occupation']
        
        is_adult_by_name = 'adult' in filename.lower()
        is_adult_by_cols = any(kw in df.columns for kw in adult_keywords)
        
        if not (is_adult_by_name or is_adult_by_cols):
            return df, False
            
        expected_cols = [
            'age', 'workclass', 'fnlwgt', 'education', 'education_num', 
            'marital_status', 'occupation', 'relationship', 'race', 'sex', 
            'capital_gain', 'capital_loss', 'hours_per_week', 'native_country', 'income'
        ]
        
        if len(df.columns) == len(expected_cols):
            df.columns = expected_cols
            
        if 'income' in df.columns:
            income_col = df['income'].astype(str).str.strip()
            df['income_binary'] = np.where(income_col == '>50K', 1, np.where(income_col == '<=50K', 0, np.nan))
            
        return df, True
