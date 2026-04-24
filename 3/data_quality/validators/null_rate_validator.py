from typing import Any, Dict, List, Optional

from .base import BaseValidator
from ..core.config import CheckStatus, CheckResult


class NullRateValidator(BaseValidator):
    CHECK_TYPE = "null_rate"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        columns = self.config.columns
        threshold = self.config.threshold

        if not table_name:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name is required for null rate check",
                errors=["Missing table_name in configuration"],
            )

        if not columns:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Columns list is required for null rate check",
                errors=["Missing columns in configuration"],
            )

        try:
            with self.connector as conn:
                total_rows = conn.get_row_count(table_name)

                if total_rows == 0:
                    return self._create_result(
                        status=CheckStatus.WARNING,
                        message=f"Table '{table_name}' is empty, cannot check null rate",
                        actual_value=0,
                        expected_value=threshold,
                        details={"total_rows": 0, "columns": columns},
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
                        message=f"All columns passed null rate check. Max null rate: {max_null_rate}%",
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
                        message=f"Null rate check failed. Failed columns: {failed_columns}",
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
