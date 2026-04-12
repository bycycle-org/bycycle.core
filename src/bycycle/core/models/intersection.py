from django.contrib.gis.db import models

from bycycle.core.geometry import DEFAULT_SRID


class Intersection(models.Model):
    class Meta:
        db_table = "intersection"

    id = models.BigAutoField(primary_key=True)
    geom = models.PointField(srid=DEFAULT_SRID)

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
