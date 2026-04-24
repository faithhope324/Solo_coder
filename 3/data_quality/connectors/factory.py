from typing import Any, Dict, Type

from .base import BaseConnector
from .sqlite_connector import SQLiteConnector
from .mysql_connector import MySQLConnector
from .postgres_connector import PostgreSQLConnector
from .csv_connector import CSVConnector
from .pandas_connector import PandasConnector


class ConnectorFactory:
    _connectors: Dict[str, Type[BaseConnector]] = {
        "sqlite": SQLiteConnector,
        "mysql": MySQLConnector,
        "postgres": PostgreSQLConnector,
        "postgresql": PostgreSQLConnector,
        "csv": CSVConnector,
        "pandas": PandasConnector,
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
        connector_class = cls._connectors[connection_type_lower]
        return connector_class(connection_params)

    @classmethod
    def get_supported_types(cls) -> list:
        return list(cls._connectors.keys())
