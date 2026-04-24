from typing import Any, Dict, List, Optional

from .base import BaseValidator
from ..core.config import CheckStatus, CheckResult


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
                message="Table name is required for row count check",
                errors=["Missing table_name in configuration"],
            )

        try:
            with self.connector as conn:
                actual_count = conn.get_row_count(table_name)

                if reference_table:
                    reference_count = conn.get_row_count(reference_table)
                    expected_value = reference_count
                elif reference_value is not None:
                    reference_count = reference_value
                    expected_value = reference_value
                else:
                    return self._create_result(
                        status=CheckStatus.ERROR,
                        message="Either reference_table or reference_value is required",
                        errors=["Missing reference configuration"],
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
                    else:
                        return self._create_result(
                            status=CheckStatus.PASS,
                            message=f"Row count check passed. Difference: {diff}, Threshold: {threshold}",
                            actual_value=actual_count,
                            expected_value=reference_count,
                            details=details,
                        )
                else:
                    if actual_count == reference_count:
                        return self._create_result(
                            status=CheckStatus.PASS,
                            message=f"Row count matches reference: {actual_count}",
                            actual_value=actual_count,
                            expected_value=reference_count,
                            details=details,
                        )
                    else:
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
