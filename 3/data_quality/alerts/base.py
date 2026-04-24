from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..core.config import CheckResult, CheckStatus, AlertLevel


class BaseAlert(ABC):
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    def send(self, result: CheckResult, alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        pass

    @abstractmethod
    def send_batch(self, results: List[CheckResult], alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        pass

    def _should_alert(self, result: CheckResult) -> bool:
        return result.status in [CheckStatus.FAIL, CheckStatus.ERROR, CheckStatus.WARNING]

    def _format_message(self, result: CheckResult) -> str:
        return f"""
Check: {result.check_name}
Type: {result.check_type}
Status: {result.status.value}
Message: {result.message}
Actual Value: {result.actual_value}
Expected Value: {result.expected_value}
Timestamp: {result.timestamp}
Execution Time: {result.execution_time_ms}ms
Errors: {result.errors if result.errors else 'None'}
Details: {result.details if result.details else 'None'}
"""
