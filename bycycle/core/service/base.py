from abc import ABCMeta, abstractmethod


class AService(metaclass=ABCMeta):

    """Base class for byCycle services."""

    def __init__(self, session, **config):
        """Initialize service.

        Args:
            session: SQLAlchemy database session
            config: Additional service-specific configuration

        """
        self.session = session
        self.config = config

    @abstractmethod
    def query(self, q, **kwargs):
        """Query this service and return a result."""
        raise NotImplementedError
