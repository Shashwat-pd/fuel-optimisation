from decimal import Decimal

MPG = 10
TANK_GALLONS = 50
RANGE_MILES = MPG * TANK_GALLONS
EPS = 1e-9


class NotEnoughStations(Exception):
    pass


def plan_fuel(stations, distance_miles, initial_gallons):
    start = {"mile": -(TANK_GALLONS - initial_gallons) * MPG, "price": Decimal(0), "virtual": True}
    stops = [start] + [s for s in stations if s["mile"] <= distance_miles]

    plan = []
    total = Decimal(0)
    i = 0
    fuel = 0.0

    while True:
        here = stops[i]
        miles_left = distance_miles - here["mile"]

        cheaper = None
        for j in range(i + 1, len(stops)):
            if stops[j]["mile"] - here["mile"] > RANGE_MILES + EPS:
                break
            if stops[j]["price"] < here["price"]:
                cheaper = j
                break

        if cheaper is not None:
            target = stops[cheaper]["mile"]
            next_i = cheaper
        elif miles_left <= RANGE_MILES + EPS:
            target = distance_miles
            next_i = None
        else:
            target = here["mile"] + RANGE_MILES
            next_i = None
            best = None
            for j in range(i + 1, len(stops)):
                if stops[j]["mile"] - here["mile"] > RANGE_MILES + EPS:
                    break
                if best is None or stops[j]["price"] <= stops[best]["price"]:
                    best = j
            if best is None:
                raise NotEnoughStations(f"No station within {RANGE_MILES} miles after mile {max(here['mile'], 0):.0f}")
            next_i = best

        needed = (target - here["mile"]) / MPG
        if here.get("virtual"):
            buy = TANK_GALLONS - fuel
        else:
            buy = max(0.0, min(needed, TANK_GALLONS) - fuel)
        arrive = fuel
        fuel += buy

        if buy > EPS and not here.get("virtual"):
            cost = here["price"] * Decimal(str(round(buy, 4)))
            total += cost
            plan.append({
                "id": here["id"],
                "name": here["name"],
                "address": here["address"],
                "latitude": here["latitude"],
                "longitude": here["longitude"],
                "price_per_gallon": str(here["price"]),
                "route_mile": round(here["mile"], 1),
                "gallons_bought": round(buy, 3),
                "cost": str(cost.quantize(Decimal("0.01"))),
                "fuel_on_arrival_gallons": round(arrive, 3),
                "fuel_on_departure_gallons": round(fuel, 3),
            })

        if next_i is None:
            fuel -= miles_left / MPG
            break
        fuel -= (stops[next_i]["mile"] - here["mile"]) / MPG
        fuel = max(fuel, 0.0)
        i = next_i

    return {
        "fuel_stops": plan,
        "total_money_spent": str(total.quantize(Decimal("0.01"))),
        "remaining_fuel_gallons": round(max(fuel, 0.0), 3),
    }
