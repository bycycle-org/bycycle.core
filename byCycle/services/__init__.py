################################################################################
# $Id$
# Created 2006-09-19.
#
# byCycle Services Package.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
"""Provides a base class for the byCycle core services."""
from byCycle.model import regions
from byCycle.model import db


class Service(object):
    """Base class for byCycle services."""

    def __init__(self, region=None):
        """Initialize service with ``region`` and database ``session``.

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
        self.region = region

    def _get_region(self):
        try:
            return self._region
        except AttributeError:
            return None
    def _set_region(self, region):
        self._region = regions.getRegion(region)
    region = property(_get_region, _set_region)

    def query(self, q, **kwargs):
        """Query this ``Service`` and return an object or objects.

        ``q`` `object`
            Query object that this ``Service`` understands

        ``kwargs``
             Typically for args that are passed through to other services.

        return an object or a collection of objects

        """
        raise NotImplementedError
