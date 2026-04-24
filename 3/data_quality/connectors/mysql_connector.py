from typing import Any, Dict, List, Optional

from .base import BaseConnector


class MySQLConnector(BaseConnector):
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.host = connection_params.get("host", "localhost")
        self.port = connection_params.get("port", 3306)
        self.user = connection_params.get("user", "root")
        self.password = connection_params.get("password", "")
        self.database = connection_params.get("database", "")

    def connect(self) -> None:
        if self._connection is None:
            try:
                import mysql.connector
                self._connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                )
            except ImportError:
                raise ImportError(
                    "mysql-connector-python is required for MySQL connections. "
                    "Install it with: pip install mysql-connector-python"
                )

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
        query = f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        cursor = self._connection.cursor()
        cursor.execute(query, (self.database, table_name))
        return [row[0] for row in cursor.fetchall()]

    def get_column_statistics(self, table_name: str, column: str) -> Dict[str, Any]:
        query = f"SELECT MIN({column}), MAX({column}), AVG({column}) FROM {table_name}"
        cursor = self._connection.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        return {
            "min": row[0],
            "max": row[1],
            "avg": float(row[2]) if row[2] is not None else None,
        }
