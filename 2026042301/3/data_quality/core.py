from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CheckStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    ERROR = "ERROR"


class AlertLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DataSourceConfig:
    name: str
    connection_type: str
    connection_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckConfig:
    name: str
    check_type: str
    data_source: str
    table_name: str = ""
    reference_table: str = ""
    columns: List[str] = field(default_factory=list)
    primary_key: str = ""
    threshold: float = 0.0
    reference_value: Optional[float] = None
    fluctuation_percent: float = 0.0
    alert_level: AlertLevel = AlertLevel.MEDIUM
    description: str = ""


@dataclass
class AlertConfig:
    enabled: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["console"])
    email_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    output_format: str = "html"
    output_path: str = "./reports"
    use_timestamp: bool = False


@dataclass
class CheckResult:
    check_name: str
    check_type: str
    status: CheckStatus
    message: str
    actual_value: Any = None
    expected_value: Any = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class DataQualityEngine:
    def __init__(
        self,
        data_sources: Optional[Dict[str, DataSourceConfig]] = None,
        alert_config: Optional[AlertConfig] = None,
        report_config: Optional[ReportConfig] = None,
    ):
        from .connectors import ConnectorFactory
        from .validators import ValidatorFactory
        from .alerts import AlertManager
        from .reports import ReportGenerator

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
        import time

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
            return CheckResult(
                check_name=check_config.name,
                check_type=check_config.check_type,
                status=CheckStatus.ERROR,
                message=f"Check failed: {str(e)}",
                timestamp=timestamp,
                execution_time_ms=execution_time,
                errors=[str(e)],
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

        for result in self.check_results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        passed = status_counts.get(CheckStatus.PASS, 0)
        failed = status_counts.get(CheckStatus.FAIL, 0) + status_counts.get(CheckStatus.WARNING, 0)
        errors = status_counts.get(CheckStatus.ERROR, 0)

        return {
            "total_checks": total,
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "passed_count": passed,
            "failed_count": failed,
            "error_count": errors,
            "all_passed": passed == total,
        }

    def generate_report(self, output_path: Optional[str] = None) -> str:
        summary = self.get_summary()
        return self.report_generator.generate(self.check_results, summary, output_path)
