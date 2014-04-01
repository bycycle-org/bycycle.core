from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger

from bycycle.core.geometry import DEFAULT_SRID
from bycycle.core.geometry.sqltypes import POINT
from bycycle.core.model import Base


class Intersection(Base):

    __tablename__ = 'intersection'

    id = Column(BigInteger, primary_key=True)
    geom = Column(POINT(DEFAULT_SRID))
    lat_long = Column(POINT(4326))

    json_fields = {
        'exclude': ['streets']  # Avoid circular reference
    }

    @property
    def name(self):
        names = list(sorted(set(s.name for s in self.streets if s.name)))
        return ' & '.join(names[:2])


from .street import Street


Intersection.streets = relationship(
    Street,
    primaryjoin=(
        (Intersection.id == Street.start_node_id) |
        (Intersection.id == Street.end_node_id)
    )
)
