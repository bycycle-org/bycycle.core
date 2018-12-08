from sqlalchemy.schema import Column
from sqlalchemy.types import Binary, String

from bycycle.core.model import Base


class MVTCache(Base):

    __tablename__ = 'mvt_cache'

    key = Column(String, primary_key=True)
    data = Column(Binary)
