import os
from typing import Any, Dict, List, Optional

from .base import BaseConnector


class CSVConnector(BaseConnector):
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.csv_path = connection_params.get("csv_path", "")
        self.delimiter = connection_params.get("delimiter", ",")
        self.encoding = connection_params.get("encoding", "utf-8")
        self.has_header = connection_params.get("has_header", True)
        self._df = None

    def connect(self) -> None:
        if self._df is None:
            try:
                import pandas as pd
            except ImportError:
                raise ImportError(
                    "pandas is required for CSV connections. "
                    "Install it with: pip install pandas"
                )

            if not os.path.exists(self.csv_path):
                raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

            self._df = pd.read_csv(
                self.csv_path,
                delimiter=self.delimiter,
                encoding=self.encoding,
                header=0 if self.has_header else None,
            )

    def disconnect(self) -> None:
        if self._df is not None:
            self._df = None

    def get_row_count(self, table_name: str = "") -> int:
        if self._df is None:
            self.connect()
        return len(self._df)

    def get_column_null_count(self, table_name: str, column: str) -> int:
        if self._df is None:
            self.connect()
        return int(self._df[column].isnull().sum())

    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        if self._df is None:
            self.connect()
        duplicate_groups = self._df.groupby(primary_key).size()
        duplicate_count = len(duplicate_groups[duplicate_groups > 1])
        return duplicate_count

    def execute_query(self, query: str) -> Any:
        raise NotImplementedError("SQL queries are not supported for CSV connector")

    def get_table_columns(self, table_name: str = "") -> List[str]:
        if self._df is None:
            self.connect()
        return list(self._df.columns)

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        if self._df is None:
            self.connect()
        try:
            column_data = self._df[column]
            if column_data.dtype.kind in 'biufc':
                return {
                    "min": column_data.min(),
                    "max": column_data.max(),
                    "avg": column_data.mean(),
                }
            else:
                return {
                    "min": None,
                    "max": None,
                    "avg": None,
                }
        except Exception:
            return {
                "min": None,
                "max": None,
                "avg": None,
            }
