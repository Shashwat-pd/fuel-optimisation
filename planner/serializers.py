from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)
    initial_fuel_gallons = serializers.FloatField(min_value=0, max_value=50, default=50.0)
