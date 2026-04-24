from typing import Any, Dict, List, Optional

from .base import BaseConnector


class PandasConnector(BaseConnector):
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self._dataframes: Dict[str, Any] = connection_params.get("dataframes", {})

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def add_dataframe(self, table_name: str, df: Any) -> None:
        self._dataframes[table_name] = df

    def get_dataframe(self, table_name: str) -> Any:
        if table_name not in self._dataframes:
            raise ValueError(f"Table/ DataFrame '{table_name}' not found")
        return self._dataframes[table_name]

    def get_row_count(self, table_name: str) -> int:
        df = self.get_dataframe(table_name)
        return len(df)

    def get_column_null_count(self, table_name: str, column: str) -> int:
        df = self.get_dataframe(table_name)
        return int(df[column].isnull().sum())

    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        df = self.get_dataframe(table_name)
        total_count = len(df)
        unique_count = df[primary_key].nunique()
        duplicate_count = total_count - unique_count
        return duplicate_count

    def execute_query(self, query: str) -> Any:
        raise NotImplementedError(
            "SQL queries are not directly supported for Pandas connector. "
            "Use pandas methods instead."
        )

    def get_table_columns(self, table_name: str) -> List[str]:
        df = self.get_dataframe(table_name)
        return list(df.columns)

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        df = self.get_dataframe(table_name)
        try:
            column_data = df[column]
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
