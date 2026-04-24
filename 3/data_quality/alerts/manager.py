from typing import Any, Dict, List, Optional

from .base import BaseAlert
from .console_alert import ConsoleAlert
from .email_alert import EmailAlert
from ..core.config import CheckResult, CheckConfig, AlertConfig, AlertLevel


class AlertManager:
    def __init__(self, alert_config: AlertConfig = None):
        self.alert_config = alert_config or AlertConfig()
        self._alerts: Dict[str, BaseAlert] = {}
        self._init_default_alerts()

    def _init_default_alerts(self) -> None:
        if "console" in self.alert_config.alert_channels:
            self._alerts["console"] = ConsoleAlert()

        if "email" in self.alert_config.alert_channels:
            email_config = self.alert_config.email_config
            if email_config:
                self._alerts["email"] = EmailAlert(email_config)

    def register_alert(self, name: str, alert: BaseAlert) -> None:
        self._alerts[name] = alert

    def unregister_alert(self, name: str) -> None:
        if name in self._alerts:
            del self._alerts[name]

    def handle_alert(self, result: CheckResult, check_config: CheckConfig) -> bool:
        if not self.alert_config.enabled:
            return True

        if not self._should_alert(result):
            return True

        alert_level = check_config.alert_level if check_config else AlertLevel.MEDIUM
        all_success = True

        for name, alert in self._alerts.items():
            try:
                success = alert.send(result, alert_level)
                if not success:
                    all_success = False
            except Exception:
                all_success = False

        return all_success

    def handle_batch_alerts(self, results: List[CheckResult], check_configs: List[CheckConfig]) -> bool:
        if not self.alert_config.enabled:
            return True

        alert_results = [r for r in results if self._should_alert(r)]
        if not alert_results:
            return True

        alert_level = self._get_highest_alert_level(alert_results, check_configs)
        all_success = True

        for name, alert in self._alerts.items():
            try:
                success = alert.send_batch(alert_results, alert_level)
                if not success:
                    all_success = False
            except Exception:
                all_success = False

        return all_success

    def _should_alert(self, result: CheckResult) -> bool:
        from ..core.config import CheckStatus
        return result.status in [CheckStatus.FAIL, CheckStatus.ERROR, CheckStatus.WARNING]

    def _get_highest_alert_level(self, results: List[CheckResult], check_configs: List[CheckConfig]) -> AlertLevel:
        level_priority = {
            AlertLevel.LOW: 1,
            AlertLevel.MEDIUM: 2,
            AlertLevel.HIGH: 3,
            AlertLevel.CRITICAL: 4,
        }

        highest_level = AlertLevel.MEDIUM
        highest_priority = level_priority[highest_level]

        for result in results:
            for config in check_configs:
                if config.name == result.check_name:
                    current_level = config.alert_level
                    current_priority = level_priority[current_level]
                    if current_priority > highest_priority:
                        highest_level = current_level
                        highest_priority = current_priority
                    break

        return highest_level

    def get_registered_alerts(self) -> List[str]:
        return list(self._alerts.keys())
