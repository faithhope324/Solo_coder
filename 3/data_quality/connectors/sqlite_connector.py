import sqlite3
from typing import Any, Dict, List, Optional

from .base import BaseConnector


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
        query = f"SELECT COUNT(*) FROM {table_name}"
        cursor = self._connection.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]

    def get_column_null_count(self, table_name: str, column: str) -> int:
        query = f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL"
        cursor = self._connection.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]

    def get_duplicate_count(self, table_name: str, primary_key: str) -> int:
        query = f"""
            SELECT COUNT(*) FROM (
                SELECT {primary_key} FROM {table_name}
                GROUP BY {primary_key}
                HAVING COUNT(*) > 1
            ) AS duplicates
        """
        cursor = self._connection.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]

    def execute_query(self, query: str) -> Any:
        cursor = self._connection.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_table_columns(self, table_name: str) -> List[str]:
        query = f"PRAGMA table_info({table_name})"
        cursor = self._connection.cursor()
        cursor.execute(query)
        return [row[1] for row in cursor.fetchall()]

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        query = f"SELECT MIN({column}), MAX({column}), AVG({column}) FROM {table_name}"
        cursor = self._connection.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        return {
            "min": row[0],
            "max": row[1],
            "avg": row[2],
        }
