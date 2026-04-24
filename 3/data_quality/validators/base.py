from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..connectors.base import BaseConnector
from ..core.config import CheckConfig, CheckResult, CheckStatus


class BaseValidator(ABC):
    def __init__(self, config: CheckConfig, connector: BaseConnector):
        self.config = config
        self.connector = connector

    @abstractmethod
    def validate(self) -> CheckResult:
        pass

    def _create_result(
        self,
        status: CheckStatus,
        message: str,
        actual_value: Any = None,
        expected_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        return CheckResult(
            check_name=self.config.name,
            check_type=self.config.check_type,
            status=status,
            message=message,
            actual_value=actual_value,
            expected_value=expected_value,
            details=details or {},
            timestamp="",
            execution_time_ms=0.0,
            errors=errors or [],
        )

    def _get_connector(self) -> BaseConnector:
        return self.connector
