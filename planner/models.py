from django.db import models


class Station(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    price = models.DecimalField(max_digits=6, decimal_places=3)
