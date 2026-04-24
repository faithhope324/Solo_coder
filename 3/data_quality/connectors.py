import os
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type


class BaseConnector(ABC):
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection_params = connection_params
        self._connection = None

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_row_count(self, table_name: str) -> int:
        pass

    @abstractmethod
    def get_column_null_count(self, table_name: str, column: str) -> int:
        pass

    @abstractmethod
    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        pass

    @abstractmethod
    def get_table_columns(self, table_name: str) -> List[str]:
        pass

    @abstractmethod
    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        pass

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()


class SQLiteConnector(BaseConnector):
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.db_path = connection_params.get("db_path", ":memory:")

    def connect(self) -> None:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def get_row_count(self, table_name: str) -> int:
        cursor = self._connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def get_column_null_count(self, table_name: str, column: str) -> int:
        cursor = self._connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL")
        return cursor.fetchone()[0]

    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        cursor = self._connection.cursor()
        cursor.execute(f"SELECT COUNT(*) - COUNT(DISTINCT {primary_key}) FROM {table_name}")
        result = cursor.fetchone()[0]
        return result if result is not None else 0

    def get_table_columns(self, table_name: str) -> List[str]:
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        cursor = self._connection.cursor()
        cursor.execute(f"SELECT MIN({column}), MAX({column}), AVG({column}) FROM {table_name}")
        row = cursor.fetchone()
        return {
            "min": row[0],
            "max": row[1],
            "avg": row[2],
        }


class PandasConnector(BaseConnector):
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self._dataframes: Dict[str, Any] = connection_params.get("dataframes", {})
        self._csv_path = connection_params.get("csv_path", "")
        self._delimiter = connection_params.get("delimiter", ",")
        self._encoding = connection_params.get("encoding", "utf-8")
        self._df = None

    def connect(self) -> None:
        if self._csv_path and self._df is None:
            try:
                import pandas as pd
            except ImportError:
                raise ImportError("pandas is required for CSV/Pandas connections")

            if not os.path.exists(self._csv_path):
                raise FileNotFoundError(f"CSV file not found: {self._csv_path}")

            self._df = pd.read_csv(self._csv_path, delimiter=self._delimiter, encoding=self._encoding)
            self._dataframes["default"] = self._df

    def disconnect(self) -> None:
        self._df = None

    def add_dataframe(self, table_name: str, df: Any) -> None:
        self._dataframes[table_name] = df

    def _get_df(self, table_name: str) -> Any:
        if table_name in self._dataframes:
            return self._dataframes[table_name]
        if self._df is not None:
            return self._df
        raise ValueError(f"Table/ DataFrame '{table_name}' not found")

    def get_row_count(self, table_name: str) -> int:
        df = self._get_df(table_name)
        return len(df)

    def get_column_null_count(self, table_name: str, column: str) -> int:
        df = self._get_df(table_name)
        return int(df[column].isnull().sum())

    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        df = self._get_df(table_name)
        total_count = len(df)
        unique_count = df[primary_key].nunique()
        return total_count - unique_count

    def get_table_columns(self, table_name: str) -> List[str]:
        df = self._get_df(table_name)
        return list(df.columns)

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        df = self._get_df(table_name)
        try:
            column_data = df[column]
            if column_data.dtype.kind in 'biufc':
                return {
                    "min": column_data.min(),
                    "max": column_data.max(),
                    "avg": column_data.mean(),
                }
        except Exception:
            pass
        return {"min": None, "max": None, "avg": None}


class ConnectorFactory:
    _connectors: Dict[str, Type[BaseConnector]] = {
        "sqlite": SQLiteConnector,
        "pandas": PandasConnector,
        "csv": PandasConnector,
    }

    @classmethod
    def register(cls, connection_type: str, connector_class: Type[BaseConnector]) -> None:
        cls._connectors[connection_type.lower()] = connector_class

    @classmethod
    def create(cls, connection_type: str, connection_params: Dict[str, Any]) -> BaseConnector:
        connection_type_lower = connection_type.lower()
        if connection_type_lower not in cls._connectors:
            raise ValueError(
                f"Unknown connection type: {connection_type}. "
                f"Supported types: {list(cls._connectors.keys())}"
            )
        return cls._connectors[connection_type_lower](connection_params)

    @classmethod
    def get_supported_types(cls) -> list:
        return list(cls._connectors.keys())
