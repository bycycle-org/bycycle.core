from sqlalchemy.schema import Column
from sqlalchemy.types import String

from . import Base


class USPSStreetSuffix(Base):

    __tablename__ = 'usps_street_suffixes'

    name = Column(String, primary_key=True)
    alias = Column(String, primary_key=True)
    abbreviation = Column(String, primary_key=True)
