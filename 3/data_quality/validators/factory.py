from typing import Any, Dict, Type

from .base import BaseValidator
from .row_count_validator import RowCountValidator
from .null_rate_validator import NullRateValidator
from .duplicate_key_validator import DuplicateKeyValidator
from .fluctuation_validator import FluctuationValidator
from ..connectors.base import BaseConnector
from ..core.config import CheckConfig


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
                f"Supported types: {list(cls._validators.keys())}"
            )
        validator_class = cls._validators[check_type_lower]
        return validator_class(config, connector)

    @classmethod
    def get_supported_types(cls) -> list:
        return list(cls._validators.keys())
