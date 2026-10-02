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
    plan = plan_fuel(stations, miles, initial_gallons)

    return {
        "start": start,
        "finish": finish,
        "distance_miles": round(miles, 1),
        "duration_minutes": round(route["duration"] / 60),
        "total_money_spent": plan["total_money_spent"],
        "fuel": {
            "start_gallons": round(plan["initial_fuel_gallons"], 2),
            "used_gallons": round(plan["fuel_consumed_gallons"], 2),
            "end_gallons": round(plan["remaining_fuel_gallons"], 2),
        },
        "fuel_stops": [
            {
                "name": stop["name"],
                "address": stop["address"],
                "latitude": stop["latitude"],
                "longitude": stop["longitude"],
                "mile": round(stop["route_mile"], 1),
                "price_per_gallon": stop["price_per_gallon"],
                "gallons": round(stop["gallons"], 2),
                "cost": stop["cost"],
            }
            for stop in plan["fuel_stops"]
            if round(stop["gallons"], 2) > 0
        ],
        "route": route["geometry"],
        "attribution": "Routing: OSRM, map data © OpenStreetMap contributors; places: US Census Bureau, GeoNames",
    }
