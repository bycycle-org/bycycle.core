from abc import ABCMeta, abstractmethod
from typing import Any


class AService(metaclass=ABCMeta):
    """Base class for byCycle services."""

    def __init__(self, **config):
        """Initialize service.

        Args:
            config: Additional service-specific configuration

        """
        self.config = config

    @abstractmethod
    def query(self, q, **kwargs) -> Any:
        """Query this service and return a result."""
        raise NotImplementedError
