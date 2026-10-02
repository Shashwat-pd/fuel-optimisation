from django.db import models


class Station(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField(db_index=True)
    longitude = models.FloatField(db_index=True)
    price = models.DecimalField(max_digits=8, decimal_places=4)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name="positive_fuel_price")]
