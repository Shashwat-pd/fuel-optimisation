from decimal import ROUND_HALF_UP, Decimal

from planner.errors import PlanError

MPG = 10
TANK_GALLONS = 50.0
RANGE_MILES = TANK_GALLONS * MPG
EPS = 1e-7


def money(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def find_breaks(miles, prices):
    breaks = []
    for i in range(len(miles)):
        cheaper_behind = False
        for j in range(i - 1, -1, -1):
            if miles[j] < miles[i] - RANGE_MILES - EPS:
                break
            if prices[j] < prices[i]:
                cheaper_behind = True
                break
        if not cheaper_behind:
            breaks.append(i)
    return breaks


def find_next_cheapest(miles, prices):
    result = [None] * len(miles)
    for i in range(len(miles)):
        best = None
        for j in range(i + 1, len(miles)):
            if miles[j] > miles[i] + RANGE_MILES + EPS:
                break
            if best is None or prices[j] <= prices[best]:
                best = j
        result[i] = best
    return result


def plan_fuel(stations, distance, initial_gallons=50):
    on_route = sorted((s for s in stations if 0 <= s["mile"] < distance), key=lambda s: (s["mile"], s["price"]))
    nodes = [{"mile": -(TANK_GALLONS - initial_gallons) * MPG, "price": Decimal(0), "station": {}}] + on_route
    miles = [n["mile"] for n in nodes]
    prices = [n["price"] for n in nodes]
    next_cheapest = find_next_cheapest(miles, prices)
    breaks = find_breaks(miles, prices)

    buy = {}
    for start, end in zip(breaks, breaks[1:] + [len(nodes)]):
        end_mile = distance if end == len(nodes) else miles[end]
        x = start
        fuel = 0.0
        while end_mile - miles[x] > RANGE_MILES + EPS:
            nxt = next_cheapest[x]
            if nxt is None:
                raise PlanError(
                    f"Insufficient station coverage near mile {max(0.0, miles[x]):.1f}; "
                    "next station/destination is unreachable.",
                    "insufficient_coverage",
                    422,
                )
            buy[x] = TANK_GALLONS - fuel
            fuel = TANK_GALLONS - (miles[nxt] - miles[x]) / MPG
            x = nxt
        buy[x] = max(0.0, (end_mile - miles[x]) / MPG - fuel)

    fuel = float(initial_gallons)
    last_mile = 0.0
    total = Decimal(0)
    stops = []
    for i in sorted(buy):
        gallons = buy[i]
        if i == 0 or gallons <= 1e-8:
            continue
        node = nodes[i]
        fuel = max(0.0, fuel - (node["mile"] - last_mile) / MPG)
        last_mile = node["mile"]
        cost = Decimal(str(gallons)) * node["price"]
        total += cost
        stops.append({
            **node["station"],
            "route_mile": round(node["mile"], 3),
            "price_per_gallon": str(node["price"]),
            "gallons": round(gallons, 6),
            "cost": money(cost),
            "arrival_gallons": round(fuel, 6),
            "departure_gallons": round(fuel + gallons, 6),
        })
        fuel += gallons
    fuel = max(0.0, fuel - (distance - last_mile) / MPG)

    return {
        "fuel_stops": stops,
        "total_money_spent": money(total),
        "fuel_consumed_gallons": round(distance / MPG, 6),
        "initial_fuel_gallons": initial_gallons,
        "remaining_fuel_gallons": round(fuel, 6),
        "currency": "USD",
    }
