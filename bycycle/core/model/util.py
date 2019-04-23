from collections import namedtuple

from shapely import wkb

from sqlalchemy.sql import func


ExtentInfo = namedtuple('ExtentInfo', 'bbox boundary center')


def get_extent(session, model, field='geom'):
    """Get extent info for ORM model or table.

    Args:
        session: Database session (or engine)
        model: ORM model (or table)
        field: model field to query for extent

    Returns:
        ExtentInfo

    """
    table = model.__table__ if hasattr(model, '__table__') else model
    q = session.execute(func.ST_Envelope(func.ST_Extent(table.c[field])))
    extent = q.scalar()
    extent = wkb.loads(extent, hex=True)
    return ExtentInfo(extent.bounds, list(extent.exterior.coords), extent.centroid.coords[0])
