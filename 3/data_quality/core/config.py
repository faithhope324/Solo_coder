from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


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
    description: str = ""
    data_source: str = ""
    table_name: str = ""
    reference_table: str = ""
    columns: List[str] = field(default_factory=list)
    primary_key: str = ""
    threshold: float = 0.0
    reference_value: Optional[float] = None
    fluctuation_percent: float = 0.0
    alert_level: AlertLevel = AlertLevel.MEDIUM
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertConfig:
    enabled: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["console"])
    email_config: Dict[str, Any] = field(default_factory=dict)
    webhook_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    output_format: str = "html"
    output_path: str = "./reports"
    include_passed_checks: bool = True
    include_charts: bool = True
    template: str = "default"
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
