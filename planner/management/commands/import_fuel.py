import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework import serializers

from planner.errors import PlanError
from planner.models import Station
from planner.places import find_city
from planner.serializers import CoordinatesSerializer

BASIC_COLUMNS = {"id", "name", "latitude", "longitude", "price"}
OPIS_COLUMNS = {"OPIS Truckstop ID", "Truckstop Name", "Address", "City", "State", "Retail Price"}


def check_coordinates(latitude, longitude):
    serializer = CoordinatesSerializer(data={"latitude": latitude, "longitude": longitude})
    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as e:
        raise PlanError(f"Invalid US coordinates: {e.detail}")
    return serializer.validated_data["latitude"], serializer.validated_data["longitude"]


def read_opis(reader):
    cheapest = {}
    skipped = 0
    for line, row in enumerate(reader, start=2):
        place = find_city(row["City"], row["State"])
        if place is None:
            skipped += 1
            continue
        try:
            price = Decimal(row["Retail Price"]).quantize(Decimal("0.0001"))
        except InvalidOperation:
            raise CommandError(f"Row {line}: invalid price")
        station_id = row["OPIS Truckstop ID"].strip()
        if station_id in cheapest and Decimal(cheapest[station_id]["price"]) <= price:
            continue
        cheapest[station_id] = {
            "id": station_id,
            "name": row["Truckstop Name"].strip(),
            "address": ", ".join(row[k].strip() for k in ("Address", "City", "State")),
            "longitude": place["longitude"],
            "latitude": place["latitude"],
            "price": str(price),
        }
    return list(cheapest.values()), skipped


class Command(BaseCommand):
    help = "Import a fuel CSV atomically: id,name,latitude,longitude,price or the assignment's OPIS file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--replace", action="store_true", help="Replace the existing station dataset")

    def handle(self, *args, **options):
        stations = []
        seen_ids = set()
        skipped = 0
        try:
            with open(options["csv_path"], newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                columns = set(reader.fieldnames or [])
                if OPIS_COLUMNS <= columns:
                    rows, skipped = read_opis(reader)
                elif BASIC_COLUMNS <= columns:
                    rows = reader
                else:
                    raise CommandError(
                        "CSV requires id,name,latitude,longitude,price (optional address) or the OPIS columns "
                        + ",".join(sorted(OPIS_COLUMNS)) + "."
                    )
                for line, row in enumerate(rows, start=2):
                    try:
                        stations.append(self.make_station(row, seen_ids))
                    except (ValueError, InvalidOperation, PlanError, TypeError, AttributeError) as e:
                        raise CommandError(f"Row {line}: {e}")
        except OSError as e:
            raise CommandError(str(e))

        if not stations:
            raise CommandError("CSV has no stations; existing dataset was preserved.")

        with transaction.atomic():
            if options["replace"]:
                Station.objects.all().delete()
            Station.objects.bulk_create(
                stations,
                batch_size=500,
                update_conflicts=True,
                unique_fields=["external_id"],
                update_fields=["name", "address", "latitude", "longitude", "price"],
            )
        self.stdout.write(self.style.SUCCESS(f"Imported {len(stations)} stations."))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {skipped} rows whose city is not a known US place."))

    def make_station(self, row, seen_ids):
        station_id = row["id"].strip()
        name = row["name"].strip()
        address = (row.get("address") or "").strip()
        if (
            not station_id or station_id in seen_ids or len(station_id) > 100
            or not name or len(name) > 200 or len(address) > 300
        ):
            raise ValueError("Invalid/duplicate id or invalid name/address length")
        latitude, longitude = check_coordinates(float(row["latitude"]), float(row["longitude"]))
        price = Decimal(row["price"])
        if not price.is_finite() or not 0 < price < 10000 or price != price.quantize(Decimal("0.0001")):
            raise ValueError("Price must be positive USD/gallon with at most four decimals")
        seen_ids.add(station_id)
        return Station(
            external_id=station_id,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            price=price,
        )
