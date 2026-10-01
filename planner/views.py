from rest_framework.response import Response
from rest_framework.views import APIView

STUB_RESPONSE = {
    "route": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}, "properties": {}},
    "fuel_stops": [],
    "total_money_spent": "0.00",
    "fuel_consumed_gallons": 0,
    "initial_fuel_gallons": 0,
    "remaining_fuel_gallons": 0,
    "distance_miles": 0,
    "duration_seconds": 0,
    "assumptions": {},
}


class RouteView(APIView):
    def post(self, request):
        return Response(STUB_RESPONSE, status=200)
