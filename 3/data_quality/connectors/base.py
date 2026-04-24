from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
    def execute_query(self, query: str) -> Any:
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
