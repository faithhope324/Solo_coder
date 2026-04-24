from typing import Any, Dict, List, Optional

from .base import BaseValidator
from ..core.config import CheckStatus, CheckResult


class DuplicateKeyValidator(BaseValidator):
    CHECK_TYPE = "duplicate_key"

    def validate(self) -> CheckResult:
        table_name = self.config.table_name
        primary_key = self.config.primary_key

        if not table_name:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Table name is required for duplicate key check",
                errors=["Missing table_name in configuration"],
            )

        if not primary_key:
            return self._create_result(
                status=CheckStatus.ERROR,
                message="Primary key is required for duplicate key check",
                errors=["Missing primary_key in configuration"],
            )

        try:
            with self.connector as conn:
                total_rows = conn.get_row_count(table_name)

                if total_rows == 0:
                    return self._create_result(
                        status=CheckStatus.WARNING,
                        message=f"Table '{table_name}' is empty, cannot check duplicate keys",
                        actual_value=0,
                        expected_value=0,
                        details={"total_rows": 0, "primary_key": primary_key},
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
                        message=f"No duplicate records found for primary key '{primary_key}'",
                        actual_value=0,
                        expected_value=0,
                        details=details,
                    )
                else:
                    return self._create_result(
                        status=CheckStatus.FAIL,
                        message=f"Found {duplicate_count} duplicate records for primary key '{primary_key}'",
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
