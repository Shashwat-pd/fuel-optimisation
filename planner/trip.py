from django.conf import settings

from planner.errors import PlanError
from planner.fuel import plan_fuel
from planner.places import find_place
from planner.routing import get_route
from planner.stations import METERS_PER_MILE, stations_along_route


def resolve(text):
    place = find_place(text)
    if place is None:
        raise PlanError(f'Could not find a US city for "{text}". Use "City, ST".', "location_not_found", 422)
    return place


def plan_trip(start_text, finish_text, initial_gallons):
    start = resolve(start_text)
    finish = resolve(finish_text)

    route = get_route(start, finish)

    miles = route["distance"] / METERS_PER_MILE
    stations = stations_along_route(route["geometry"], miles)
    result = plan_fuel(stations, miles, initial_gallons)

    result.update(
        {
            "distance_miles": round(miles, 3),
            "duration_seconds": round(route["duration"]),
            "route": {"type": "Feature", "geometry": route["geometry"], "properties": {}},
            "start": [start["longitude"], start["latitude"]],
            "finish": [finish["longitude"], finish["latitude"]],
            "start_name": start["name"],
            "finish_name": finish["name"],
            "assumptions": {
                "mpg": 10,
                "tank_capacity_gallons": 50,
                "range_miles": 500,
                "initial_fuel_cost": "Existing fuel is treated as prepaid and excluded from total_money_spent.",
                "optimization": "Minimum purchase cost on the supplied fixed route, assuming station access adds no mileage.",
                "station_location": "The fuel file has no coordinates, so each station is placed at its city's center.",
                "endpoints": "Start and finish are city centers.",
                "station_access": f"Stations within {settings.STATION_CORRIDOR_MILES} miles of the route are considered; "
                "road access and detours are not verified. Costs and range are estimates; retain a fuel reserve.",
                "route_choice": "OSRM driving route, not a globally minimum-cost route.",
            },
            "attribution": "Routing: OSRM; map data © OpenStreetMap contributors; "
            "places: US Census Bureau, GeoNames (CC BY 4.0)",
        }
    )
    return result
