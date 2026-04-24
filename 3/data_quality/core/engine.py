import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..connectors import ConnectorFactory
from ..validators import ValidatorFactory
from ..alerts import AlertManager
from ..reports import ReportGenerator
from .config import (
    CheckConfig,
    CheckResult,
    CheckStatus,
    AlertConfig,
    ReportConfig,
    DataSourceConfig,
)


class DataQualityEngine:
    def __init__(
        self,
        data_sources: Optional[Dict[str, DataSourceConfig]] = None,
        alert_config: Optional[AlertConfig] = None,
        report_config: Optional[ReportConfig] = None,
    ):
        self.data_sources = data_sources or {}
        self.alert_config = alert_config or AlertConfig()
        self.report_config = report_config or ReportConfig()
        self.connector_factory = ConnectorFactory()
        self.validator_factory = ValidatorFactory()
        self.alert_manager = AlertManager(self.alert_config)
        self.report_generator = ReportGenerator(self.report_config)
        self.check_results: List[CheckResult] = []

    def add_data_source(self, config: DataSourceConfig) -> None:
        self.data_sources[config.name] = config

    def run_check(self, check_config: CheckConfig) -> CheckResult:
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        try:
            data_source = self.data_sources.get(check_config.data_source)
            if not data_source:
                return CheckResult(
                    check_name=check_config.name,
                    check_type=check_config.check_type,
                    status=CheckStatus.ERROR,
                    message=f"Data source '{check_config.data_source}' not found",
                    timestamp=timestamp,
                    execution_time_ms=0.0,
                    errors=[f"Data source '{check_config.data_source}' not configured"],
                )

            connector = self.connector_factory.create(
                data_source.connection_type, data_source.connection_params
            )

            validator = self.validator_factory.create(
                check_config.check_type, check_config, connector
            )

            result = validator.validate()
            result.timestamp = timestamp
            result.execution_time_ms = (time.time() - start_time) * 1000

            if self.alert_config.enabled:
                self.alert_manager.handle_alert(result, check_config)

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_message = str(e)
            return CheckResult(
                check_name=check_config.name,
                check_type=check_config.check_type,
                status=CheckStatus.ERROR,
                message=f"Check execution failed: {error_message}",
                timestamp=timestamp,
                execution_time_ms=execution_time,
                errors=[error_message],
            )

    def run_checks(self, check_configs: List[CheckConfig]) -> List[CheckResult]:
        self.check_results = []
        for check_config in check_configs:
            result = self.run_check(check_config)
            self.check_results.append(result)
        return self.check_results

    def get_summary(self) -> Dict[str, Any]:
        if not self.check_results:
            return {"total_checks": 0, "status_counts": {}}

        total = len(self.check_results)
        status_counts: Dict[CheckStatus, int] = {}
        failed_checks = []
        error_checks = []

        for result in self.check_results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            if result.status in [CheckStatus.FAIL, CheckStatus.WARNING]:
                failed_checks.append(result)
            if result.status == CheckStatus.ERROR:
                error_checks.append(result)

        return {
            "total_checks": total,
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "passed_count": status_counts.get(CheckStatus.PASS, 0),
            "failed_count": status_counts.get(CheckStatus.FAIL, 0)
            + status_counts.get(CheckStatus.WARNING, 0),
            "error_count": status_counts.get(CheckStatus.ERROR, 0),
            "failed_checks": failed_checks,
            "error_checks": error_checks,
            "all_passed": status_counts.get(CheckStatus.PASS, 0) == total,
        }

    def generate_report(self, output_path: Optional[str] = None) -> str:
        summary = self.get_summary()
        return self.report_generator.generate(self.check_results, summary, output_path)
