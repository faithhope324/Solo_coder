from typing import Any, Dict, List, Optional

from .base import BaseValidator
from ..core.config import CheckStatus, CheckResult


class FluctuationValidator(BaseValidator):
    CHECK_TYPE = "fluctuation"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        reference_value = self.config.reference_value
        fluctuation_percent = self.config.fluctuation_percent
        column = self.config.columns[0] if self.config.columns else None

        if not table_name:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name is required for fluctuation check",
                errors=["Missing table_name in configuration"],
            )

        if reference_value is None:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Reference value is required for fluctuation check",
                errors=["Missing reference_value in configuration"],
            )

        if fluctuation_percent <= 0:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Fluctuation percentage must be greater than 0",
                errors=["Invalid fluctuation_percent value"],
            )

        try:
            with self.connector as conn:
                if column:
                    stats = conn.get_column_statistics(table_name, column)
                    current_value = stats.get("avg") or stats.get("sum")
                    if current_value is None:
                        current_value = conn.get_row_count(table_name)
                else:
                    current_value = conn.get_row_count(table_name)

                if current_value is None:
                    return self._create_result(
                        status=CheckStatus.ERROR,
                        message="Could not determine current value for fluctuation check",
                        errors=["Failed to get current value from data source"],
                    )

                if reference_value == 0:
                    if current_value == 0:
                        return self._create_result(
                            status=CheckStatus.PASS,
                            message="Both current and reference values are 0, no fluctuation",
                            actual_value=current_value,
                            expected_value=reference_value,
                            details={
                                "current_value": current_value,
                                "reference_value": reference_value,
                                "fluctuation_percent": 0,
                                "threshold_percent": fluctuation_percent,
                            },
                        )
                    else:
                        return self._create_result(
                            status=CheckStatus.FAIL,
                            message=f"Reference value is 0 but current value is {current_value}, fluctuation detected",
                            actual_value=current_value,
                            expected_value=reference_value,
                            details={
                                "current_value": current_value,
                                "reference_value": reference_value,
                                "fluctuation_percent": float("inf"),
                                "threshold_percent": fluctuation_percent,
                            },
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
                        message=f"Fluctuation exceeds threshold. {direction} of {fluctuation_pct}% (threshold: {fluctuation_percent}%)",
                        actual_value=current_value,
                        expected_value=reference_value,
                        details=details,
                    )
                else:
                    return self._create_result(
                        status=CheckStatus.PASS,
                        message=f"Fluctuation within acceptable range. {fluctuation_pct}% (threshold: {fluctuation_percent}%)",
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
