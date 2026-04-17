from django.contrib.gis.db import models
from django.db.models.manager import Manager

from bycycle.core.geometry import DEFAULT_SRID


class Intersection(models.Model):
    class Meta:
        db_table = "intersection"

    id = models.BigAutoField(primary_key=True)
    geom = models.PointField(srid=DEFAULT_SRID)

    start_streets: Manager[Street]
    end_streets: Manager[Street]

    json_fields = {
        "include": ["*", "name"],
        "exclude": ["streets"],  # Avoid circular reference
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
        return " & ".join(names[:2])

    @property
    def name(self):
        return self.name_for_cross_streets(self.streets)

    @property
    def streets(self) -> tuple[Street, ...]:
        return tuple(self.start_streets.all()) + tuple(self.end_streets.all())

    def __str__(self):
        return f"Intersection {self.id}: {self.name or "[unnamed]"}"


from .street import Street  # noqa: E402
