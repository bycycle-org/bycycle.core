from abc import ABCMeta, abstractmethod


class AService(metaclass=ABCMeta):

    """Base class for byCycle services."""

    def __init__(self, session):
        """Initialize service with database ``session``."""
        self.session = session

    @abstractmethod
    def query(self, q, **kwargs):
        """Query this service and return a result."""
        raise NotImplementedError
