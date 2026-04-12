from django.db import models


class MVTCache(models.Model):
    class Meta:
        db_table = "mvt_cache"

    key = models.CharField(primary_key=True)
    data = models.BinaryField()
