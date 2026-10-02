import math

from rest_framework import serializers

from planner.geography import in_us


class NumberField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            self.fail("invalid")
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail("invalid")
        return value


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)
    initial_fuel_gallons = NumberField(min_value=0, max_value=50, default=50.0)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["Unknown field."] for key in unknown})
        return super().to_internal_value(data)


class CoordinatesSerializer(serializers.Serializer):
    latitude = NumberField(min_value=-90, max_value=90)
    longitude = NumberField(min_value=-180, max_value=180)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["Unknown field."] for key in unknown})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not in_us(attrs["latitude"], attrs["longitude"]):
            raise serializers.ValidationError("Location must be on US land (including Alaska and Hawaii).")
        return attrs
