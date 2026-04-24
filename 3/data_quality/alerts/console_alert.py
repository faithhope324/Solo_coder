from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseAlert
from ..core.config import CheckResult, CheckStatus, AlertLevel


class ConsoleAlert(BaseAlert):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.include_details = self.config.get("include_details", True)

    def send(self, result: CheckResult, alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        if not self._should_alert(result):
            return True

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_color = self._get_status_color(result.status)
            reset_color = "\033[0m"

            header = f"[{timestamp}] [{alert_level.value}] DATA QUALITY ALERT"
            print(f"{status_color}{header}{reset_color}")
            print("=" * 60)
            print(f"Check Name: {result.check_name}")
            print(f"Check Type: {result.check_type}")
            print(f"Status: {result.status.value}")
            print(f"Message: {result.message}")
            print(f"Actual Value: {result.actual_value}")
            print(f"Expected Value: {result.expected_value}")

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
        status_color = self._get_status_color(CheckStatus.FAIL)
        reset_color = "\033[0m"

        header = f"[{timestamp}] [{alert_level.value}] BATCH DATA QUALITY ALERT - {len(alert_results)} issues found"
        print(f"{status_color}{header}{reset_color}")
        print("=" * 60)

        for i, result in enumerate(alert_results, 1):
            print(f"\n--- Alert {i} ---")
            print(f"Check Name: {result.check_name}")
            print(f"Status: {result.status.value}")
            print(f"Message: {result.message}")

        print("\n" + "=" * 60)
        return True

    def _get_status_color(self, status: CheckStatus) -> str:
        color_map = {
            CheckStatus.PASS: "\033[92m",
            CheckStatus.WARNING: "\033[93m",
            CheckStatus.FAIL: "\033[91m",
            CheckStatus.ERROR: "\033[95m",
        }
        return color_map.get(status, "\033[0m")
