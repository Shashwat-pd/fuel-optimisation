from rest_framework.response import Response
from rest_framework.views import APIView

from planner.serializers import RouteRequestSerializer
from planner.trip import plan_trip


class RouteView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(plan_trip(data["start"], data["finish"], data["initial_fuel_gallons"]))
