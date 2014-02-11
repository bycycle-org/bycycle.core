"""Provides a base class for the byCycle core services."""
from bycycle.core.model.regions import  getRegionKey
from bycycle.core.model import Region


class Service(object):
    """Base class for byCycle services."""

    def __init__(self, session, region=None):
        """Initialize service with ``region`` and database ``session``.

        ``session`` A SQLAlchemy database session.

        ``region`` string | ``Region`` | None
            Either a region key or a `Region` object. In the first case a new
            ``Region`` will be instantiated; in the second, the object will be
            used directly. ``region`` need not be specified; if it isn't, a
            specific service can try to guess it (most likely via the address
            normalization ``Service``).

        raise ValueError
            ``region`` is not a known region key or alias, a ``Region``
            instance, or None.

        """
        self.session = session
        self.region = region

    @property
    def region(self):
        try:
            return self._region
        except AttributeError:
            return None

    @region.setter
    def region(self, region):
        if region:
            if not isinstance(region, Region):
                region_key = getRegionKey(region)
                if region_key == 'all':
                    region = None
                else:
                    q = self.session.query(Region)
                    q = q.filter_by(slug=region_key)
                    region = q.one()
        else:
            region = None
        self._region = region

    def query(self, q, **kwargs):
        """Query this ``Service`` and return an object or objects.

        ``q`` `object`
            Query object that this ``Service`` understands

        ``kwargs``
             Typically for args that are passed through to other services.

        return an object or a collection of objects

        """
        raise NotImplementedError
