from rest_framework import serializers


class CoordinatesSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class RouteRequestSerializer(serializers.Serializer):
    start = CoordinatesSerializer()
    finish = CoordinatesSerializer()
    initial_fuel_gallons = serializers.FloatField(min_value=0, max_value=50, default=50.0)
