from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger, Integer

from bycycle.core.geometry import DEFAULT_SRID
from bycycle.core.geometry.sqltypes import POINT
from bycycle.core.model import Base


class Intersection(Base):

    __tablename__ = 'intersection'

    id = Column(BigInteger, primary_key=True)
    geom = Column(POINT(DEFAULT_SRID))

    json_fields = {
        'include': ['*', 'name'],
        'exclude': ['streets']  # Avoid circular reference
    }

    @classmethod
    def name_for_cross_streets(cls, streets):
        names = {}

        for street in streets:
            name = street.name
            if name:
                parts = name.split()
                key = tuple(parts[1:])
                names[key] = name

        names = sorted(names.values())
        return ' & '.join(names[:2])

    @property
    def name(self):
        return self.name_for_cross_streets(self.streets)


from .street import Street


Intersection.streets = relationship(
    Street,
    primaryjoin=(
        (Intersection.id == Street.start_node_id) |
        (Intersection.id == Street.end_node_id)
    )
)
