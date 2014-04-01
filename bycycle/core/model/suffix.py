from sqlalchemy.schema import Column
from sqlalchemy.types import String

from tangled.util import asset_path

from . import Base


class USPSStreetSuffix(Base):

    __tablename__ = 'usps_street_suffix'

    name = Column(String, primary_key=True)
    alias = Column(String, primary_key=True)
    abbreviation = Column(String, primary_key=True)

    @classmethod
    def initialize(cls, executor):
        table_name = cls.__tablename__
        columns = ', '.join(c.name for c in cls.__table__.c)
        path = asset_path('bycycle.core.model', '{}.csv'.format(table_name))
        executor.execute('DELETE FROM {}'.format(table_name))
        sql = (
            "COPY {table_name}({columns}) "
            "FROM '{path}' "
            "DELIMITER ',' "
            "CSV "
            "HEADER"
        ).format(table_name=table_name, columns=columns, path=path)
        executor.execute(sql)
        executor.commit()
