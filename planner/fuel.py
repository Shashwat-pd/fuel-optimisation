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

    on_route = sorted(
        (s for s in stations if 0 <= s["mile"] < distance),
        key=lambda s: (s["mile"], s["price"]),
    )

    # assume: we filled a full tank for free somewhere behind the start?
    free_fill = {"mile": -(TANK_GALLONS - initial_gallons) * MPG, "price": Decimal(0), "station": {}}
    nodes = [free_fill, *on_route]
    miles = [n["mile"] for n in nodes]  # route mile of each stop
    prices = [n["price"] for n in nodes]

    next_cheapest = find_next_cheapest(miles, prices)
    breaks = find_breaks(miles, prices)
    finish = len(nodes)

    # A "break" is a station with nothing cheaper in the 500 miles behind it, so it's
    # a good place to arrive nearly empty. Plan each stretch between breaks on its own.
    buy = {}
    for here, end in zip(breaks, [*breaks[1:], finish]):
        end_mile = distance if end == finish else miles[end]
        fuel = 0.0

        # Too far to reach the end of this stretch in one go: fill up and hop to the
        # cheapest station within range, and repeat until the end is reachable.
        while end_mile - miles[here] > RANGE_MILES + EPS:
            hop = next_cheapest[here]
            if hop is None:
                raise PlanError(
                    f"Insufficient station coverage near mile {max(0.0, miles[here]):.1f}; "
                    "next station/destination is unreachable.",
                    "insufficient_coverage",
                    422,
                )
            buy[here] = TANK_GALLONS - fuel
            fuel = TANK_GALLONS - (miles[hop] - miles[here]) / MPG
            here = hop

        # The end is in reach now, so buy just enough to get there.
        buy[here] = max(0.0, (end_mile - miles[here]) / MPG - fuel)

    # Drive the plan again from the real starting tank to work out what the
    # gauge reads at each stop and what each fill-up costs.
    fuel = float(initial_gallons)
    last_mile = 0.0
    total = Decimal(0)
    stops = []
    for i, gallons in sorted(buy.items()):
        # Skip the free fill and any purchase too small to matter.
        if i == 0 or gallons <= 1e-8:
            continue
        node = nodes[i]
        fuel = max(0.0, fuel - (node["mile"] - last_mile) / MPG)
        last_mile = node["mile"]
        cost = Decimal(str(gallons)) * node["price"]
        total += cost
        stops.append(
            {
                **node["station"],
                "route_mile": round(node["mile"], 3),
                "price_per_gallon": str(node["price"]),
                "gallons": round(gallons, 6),
                "cost": money(cost),
                "arrival_gallons": round(fuel, 6),
                "departure_gallons": round(fuel + gallons, 6),
            }
        )
        fuel += gallons

    # Whatever is left after the last leg to the finish.
    fuel = max(0.0, fuel - (distance - last_mile) / MPG)

    return {
        "fuel_stops": stops,
        "total_money_spent": money(total),
        "fuel_consumed_gallons": round(distance / MPG, 6),
        "initial_fuel_gallons": initial_gallons,
        "remaining_fuel_gallons": round(fuel, 6),
        "currency": "USD",
    }
