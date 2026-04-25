from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .core import CheckResult, CheckStatus, CheckConfig, AlertLevel, AlertConfig


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


class ConsoleAlert(BaseAlert):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.include_details = self.config.get("include_details", True)

    def send(self, result: CheckResult, alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        if not self._should_alert(result):
            return True

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_map = {
                CheckStatus.PASS: "INFO",
                CheckStatus.WARNING: "WARNING",
                CheckStatus.FAIL: "FAIL",
                CheckStatus.ERROR: "ERROR",
            }
            status_str = status_map.get(result.status, "UNKNOWN")

            print(f"\n[{timestamp}] [{alert_level.value}] [{status_str}] DATA QUALITY ALERT")
            print("=" * 60)
            print(f"Check Name: {result.check_name}")
            print(f"Check Type: {result.check_type}")
            print(f"Message: {result.message}")
            print(f"Actual: {result.actual_value}")
            print(f"Expected: {result.expected_value}")

            if self.include_details and result.details:
                print("\nDetails:")
                for key, value in result.details.items():
                    print(f"  - {key}: {value}")

            if result.errors:
                print("\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")

            print("=" * 60)
            return True

        except Exception:
            return False

    def send_batch(self, results: List[CheckResult], alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        alert_results = [r for r in results if self._should_alert(r)]

        if not alert_results:
            return True

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] [{alert_level.value}] BATCH ALERT - {len(alert_results)} issues")
        print("=" * 60)

        for i, result in enumerate(alert_results, 1):
            print(f"\n--- {i}. {result.check_name} ---")
            print(f"Status: {result.status.value}")
            print(f"Message: {result.message}")

        print("\n" + "=" * 60)
        return True


class AlertManager:
    def __init__(self, alert_config: AlertConfig = None):
        self.alert_config = alert_config or AlertConfig()
        self._alerts: Dict[str, BaseAlert] = {}
        self._init_default_alerts()

    def _init_default_alerts(self) -> None:
        if "console" in self.alert_config.alert_channels:
            self._alerts["console"] = ConsoleAlert()

    def register_alert(self, name: str, alert: BaseAlert) -> None:
        self._alerts[name] = alert

    def handle_alert(self, result: CheckResult, check_config: CheckConfig) -> bool:
        if not self.alert_config.enabled:
            return True

        if not result.status in [CheckStatus.FAIL, CheckStatus.ERROR, CheckStatus.WARNING]:
            return True

        alert_level = check_config.alert_level if check_config else AlertLevel.MEDIUM
        all_success = True

        for alert in self._alerts.values():
            try:
                if not alert.send(result, alert_level):
                    all_success = False
            except Exception:
                all_success = False

        return all_success

    def get_registered_alerts(self) -> List[str]:
        return list(self._alerts.keys())
