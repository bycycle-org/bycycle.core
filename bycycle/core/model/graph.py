import datetime

from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger, Binary, DateTime

from bycycle.core.model import Base


class Graph(Base):

    __tablename__ = 'graphs'

    id = Column(BigInteger, primary_key=True)
    data = Column(Binary, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
