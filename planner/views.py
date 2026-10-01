import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from planner.fuel import MPG, NotEnoughStations, plan_fuel
from planner.places import find_place
from planner.routing import RouteNotFound, get_route
from planner.serializers import RouteRequestSerializer
from planner.stations import stations_along_route


class RouteView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        start = find_place(data["start"])
        finish = find_place(data["finish"])
        for text, place in ((data["start"], start), (data["finish"], finish)):
            if place is None:
                return Response({"error": f'Could not find "{text}". Use "City, ST".'}, status=422)

        try:
            route = get_route(start, finish)
        except RouteNotFound as e:
            return Response({"error": str(e)}, status=422)
        except (requests.RequestException, ValueError):
            return Response({"error": "Routing service unavailable"}, status=502)

        stations = stations_along_route(route["geometry"], route["distance_miles"])
        try:
            fuel = plan_fuel(stations, route["distance_miles"], data["initial_fuel_gallons"])
        except NotEnoughStations as e:
            return Response({"error": str(e)}, status=422)

        return Response({
            "route": {"type": "Feature", "geometry": route["geometry"], "properties": {}},
            "start": [start["longitude"], start["latitude"]],
            "finish": [finish["longitude"], finish["latitude"]],
            "start_name": start["name"],
            "finish_name": finish["name"],
            "fuel_stops": fuel["fuel_stops"],
            "total_money_spent": fuel["total_money_spent"],
            "fuel_consumed_gallons": round(route["distance_miles"] / MPG, 3),
            "initial_fuel_gallons": data["initial_fuel_gallons"],
            "remaining_fuel_gallons": fuel["remaining_fuel_gallons"],
            "distance_miles": round(route["distance_miles"], 1),
            "duration_seconds": route["duration_seconds"],
            "assumptions": {
                "mpg": MPG,
                "stations_searched": len(stations),
                "station_locations": "city centers, within 5 miles of the route",
            },
        })
