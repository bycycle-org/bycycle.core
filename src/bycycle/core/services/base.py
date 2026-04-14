from abc import ABCMeta, abstractmethod
from typing import Any


class AService(metaclass=ABCMeta):
    """Base class for byCycle services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provides the name of this service."""
        raise NotImplementedError

    @abstractmethod
    def query(self, q, **kwargs) -> Any:
        """Query this service and return a result."""
        raise NotImplementedError
