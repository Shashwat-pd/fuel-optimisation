import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from planner.routing import RouteNotFound, get_route
from planner.serializers import RouteRequestSerializer


class RouteView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            route = get_route(data["start"], data["finish"])
        except RouteNotFound as e:
            return Response({"error": str(e)}, status=422)
        except (requests.RequestException, ValueError):
            return Response({"error": "Routing service unavailable"}, status=502)

        return Response({
            "route": {"type": "Feature", "geometry": route["geometry"], "properties": {}},
            "fuel_stops": [],
            "total_money_spent": "0.00",
            "fuel_consumed_gallons": 0,
            "initial_fuel_gallons": data["initial_fuel_gallons"],
            "remaining_fuel_gallons": 0,
            "distance_miles": round(route["distance_miles"], 1),
            "duration_seconds": route["duration_seconds"],
            "assumptions": {},
        })
