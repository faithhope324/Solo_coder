from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from .connectors import BaseConnector
from .core import CheckConfig, CheckResult, CheckStatus


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


class RowCountValidator(BaseValidator):
    CHECK_TYPE = "row_count"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        reference_table = self.config.reference_table
        reference_value = self.config.reference_value
        threshold = self.config.threshold

        if not table_name:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name is required",
                errors=["Missing table_name"],
            )

        try:
            with self.connector as conn:
                actual_count = conn.get_row_count(table_name)

                if reference_table:
                    reference_count = conn.get_row_count(reference_table)
                elif reference_value is not None:
                    reference_count = reference_value
                else:
                    return self._create_result(
                        status=CheckStatus.ERROR,
                        message="Either reference_table or reference_value is required",
                        errors=["Missing reference"],
                    )

                diff = abs(actual_count - reference_count)
                diff_percent = (diff / reference_count * 100) if reference_count > 0 else 0

                details = {
                    "actual_count": actual_count,
                    "reference_count": reference_count,
                    "difference": diff,
                    "difference_percent": round(diff_percent, 2),
                    "threshold": threshold,
                }

                if threshold > 0:
                    if diff > threshold:
                        return self._create_result(
                            status=CheckStatus.FAIL,
                            message=f"Row count difference ({diff}) exceeds threshold ({threshold})",
                            actual_value=actual_count,
                            expected_value=reference_count,
                            details=details,
                        )
                    return self._create_result(
                        status=CheckStatus.PASS,
                        message=f"Row count check passed. Difference: {diff}",
                        actual_value=actual_count,
                        expected_value=reference_count,
                        details=details,
                    )
                else:
                    if actual_count == reference_count:
                        return self._create_result(
                            status=CheckStatus.PASS,
                            message=f"Row count matches: {actual_count}",
                            actual_value=actual_count,
                            expected_value=reference_count,
                            details=details,
                        )
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Row count mismatch. Expected: {reference_count}, Actual: {actual_count}",
                        actual_value=actual_count,
                        expected_value=reference_count,
                        details=details,
                    )

        except Exception as e:
            return self._create_result(
                status=CheckStatus.ERROR,
                message=f"Row count check failed: {str(e)}",
                errors=[str(e)],
            )


class NullRateValidator(BaseValidator):
    CHECK_TYPE = "null_rate"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        columns = self.config.columns
        threshold = self.config.threshold

        if not table_name or not columns:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name and columns are required",
                errors=["Missing table_name or columns"],
            )

        try:
            with self.connector as conn:
                total_rows = conn.get_row_count(table_name)

                if total_rows == 0:
                    return self._create_result(
                        status=CheckStatus.WARNING,
                        message=f"Table '{table_name}' is empty",
                        actual_value=0,
                        expected_value=threshold,
                        details={"total_rows": 0},
                    )

                column_results = {}
                all_passed = True
                max_null_rate = 0.0

                for column in columns:
                    null_count = conn.get_column_null_count(table_name, column)
                    null_rate = (null_count / total_rows) * 100
                    null_rate = round(null_rate, 4)

                    column_results[column] = {
                        "null_count": null_count,
                        "total_count": total_rows,
                        "null_rate_percent": null_rate,
                        "threshold": threshold,
                        "passed": null_rate <= threshold,
                    }

                    if null_rate > threshold:
                        all_passed = False
                    max_null_rate = max(max_null_rate, null_rate)

                details = {
                    "total_rows": total_rows,
                    "threshold_percent": threshold,
                    "columns": column_results,
                    "max_null_rate": max_null_rate,
                }

                if all_passed:
                    return self._create_result(
                        status=CheckStatus.PASS,
                        message=f"All columns passed. Max null rate: {max_null_rate}%",
                        actual_value=max_null_rate,
                        expected_value=threshold,
                        details=details,
                    )
                else:
                    failed_columns = [
                        col for col, result in column_results.items()
                        if not result["passed"]
                    ]
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Null rate check failed. Columns: {failed_columns}",
                        actual_value=max_null_rate,
                        expected_value=threshold,
                        details=details,
                    )

        except Exception as e:
            return self._create_result(
                status=CheckStatus.ERROR,
                message=f"Null rate check failed: {str(e)}",
                errors=[str(e)],
            )


class DuplicateKeyValidator(BaseValidator):
    CHECK_TYPE = "duplicate_key"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        primary_key = self.config.primary_key

        if not table_name or not primary_key:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name and primary key are required",
                errors=["Missing table_name or primary_key"],
            )

        try:
            with self.connector as conn:
                total_rows = conn.get_row_count(table_name)

                if total_rows == 0:
                    return self._create_result(
                        status=CheckStatus.WARNING,
                        message=f"Table '{table_name}' is empty",
                        actual_value=0,
                        expected_value=0,
                        details={"total_rows": 0},
                    )

                duplicate_count = conn.get_duplicate_count(table_name, primary_key)

                details = {
                    "total_rows": total_rows,
                    "primary_key": primary_key,
                    "duplicate_records_count": duplicate_count,
                }

                if duplicate_count == 0:
                    return self._create_result(
                        status=CheckStatus.PASS,
                        message=f"No duplicate records found for '{primary_key}'",
                        actual_value=0,
                        expected_value=0,
                        details=details,
                    )
                else:
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Found {duplicate_count} duplicate records for '{primary_key}'",
                        actual_value=duplicate_count,
                        expected_value=0,
                        details=details,
                    )

        except Exception as e:
            return self._create_result(
                status=CheckStatus.ERROR,
                message=f"Duplicate key check failed: {str(e)}",
                errors=[str(e)],
            )


class FluctuationValidator(BaseValidator):
    CHECK_TYPE = "fluctuation"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        reference_value = self.config.reference_value
        fluctuation_percent = self.config.fluctuation_percent
        column = self.config.columns[0] if self.config.columns else None

        if not table_name or reference_value is None or fluctuation_percent <= 0:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name, reference_value and fluctuation_percent are required",
                errors=["Missing required parameters"],
            )

        try:
            with self.connector as conn:
                if column:
                    stats = conn.get_column_statistics(table_name, column)
                    current_value = stats.get("avg")
                    if current_value is None:
                        current_value = conn.get_row_count(table_name)
                else:
                    current_value = conn.get_row_count(table_name)

                if current_value is None:
                    return self._create_result(
                        status=CheckStatus.ERROR,
                        message="Could not determine current value",
                        errors=["Failed to get current value"],
                    )

                if reference_value == 0:
                    if current_value == 0:
                        return self._create_result(
                            status=CheckStatus.PASS,
                            message="Both values are 0, no fluctuation",
                            actual_value=current_value,
                            expected_value=reference_value,
                        )
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Reference is 0 but current is {current_value}",
                        actual_value=current_value,
                        expected_value=reference_value,
                    )

                fluctuation = abs(current_value - reference_value)
                fluctuation_pct = (fluctuation / reference_value) * 100
                fluctuation_pct = round(fluctuation_pct, 4)

                details = {
                    "current_value": current_value,
                    "reference_value": reference_value,
                    "difference": current_value - reference_value,
                    "fluctuation_percent": fluctuation_pct,
                    "threshold_percent": fluctuation_percent,
                }

                if fluctuation_pct > fluctuation_percent:
                    direction = "increase" if current_value > reference_value else "decrease"
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Fluctuation exceeds threshold. {direction} of {fluctuation_pct}%",
                        actual_value=current_value,
                        expected_value=reference_value,
                        details=details,
                    )
                else:
                    return self._create_result(
                        status=CheckStatus.PASS,
                        message=f"Fluctuation within range: {fluctuation_pct}%",
                        actual_value=current_value,
                        expected_value=reference_value,
                        details=details,
                    )

        except Exception as e:
            return self._create_result(
                status=CheckStatus.ERROR,
                message=f"Fluctuation check failed: {str(e)}",
                errors=[str(e)],
            )


class ValidatorFactory:
    _validators: Dict[str, Type[BaseValidator]] = {
        "row_count": RowCountValidator,
        "null_rate": NullRateValidator,
        "duplicate_key": DuplicateKeyValidator,
        "fluctuation": FluctuationValidator,
    }

    @classmethod
    def register(cls, check_type: str, validator_class: Type[BaseValidator]) -> None:
        cls._validators[check_type.lower()] = validator_class

    @classmethod
    def create(
        cls,
        check_type: str,
        config: CheckConfig,
        connector: BaseConnector,
    ) -> BaseValidator:
        check_type_lower = check_type.lower()
        if check_type_lower not in cls._validators:
            raise ValueError(
                f"Unknown check type: {check_type}. "
                f"Supported: {list(cls._validators.keys())}"
            )
        return cls._validators[check_type_lower](config, connector)

    @classmethod
    def get_supported_types(cls) -> list:
        return list(cls._validators.keys())
