from django.db import models


class USPSStreetSuffix(models.Model):
    class Meta:
        db_table = "usps_street_suffix"

    pk = models.CompositePrimaryKey("name", "alias", "abbreviation")

    name = models.CharField()
    alias = models.CharField()
    abbreviation = models.CharField()
