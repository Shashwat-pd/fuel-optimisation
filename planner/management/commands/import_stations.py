import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.models import Station
from planner.places import find_place

REQUIRED_COLUMNS = {"id", "name", "latitude", "longitude", "price"}
OPIS_COLUMNS = {"OPIS Truckstop ID", "Truckstop Name", "Address", "City", "State", "Retail Price"}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **options):
        try:
            with open(options["path"], newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                columns = set(reader.fieldnames or [])
                skipped = 0
                if OPIS_COLUMNS <= columns:
                    rows, skipped = self.opis_rows(reader)
                else:
                    missing = REQUIRED_COLUMNS - columns
                    if missing:
                        raise CommandError(f"Missing columns: {', '.join(sorted(missing))}")
                    rows = enumerate(reader, start=2)
                stations = []
                seen_ids = set()
                for line, row in rows:
                    try:
                        stations.append(self.parse_row(row, seen_ids))
                    except (ValueError, TypeError) as e:
                        raise CommandError(f"Line {line}: {e}")
        except OSError as e:
            raise CommandError(str(e))

        if not stations:
            raise CommandError("No stations in file, nothing imported")

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
        self.stdout.write(self.style.SUCCESS(f"Imported {len(stations)} stations"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {skipped} rows with an unknown city"))

    def opis_rows(self, reader):
        cheapest = {}
        skipped = 0
        for line, row in enumerate(reader, start=2):
            place = find_place(f"{row['City']}, {row['State']}")
            if place is None:
                skipped += 1
                continue
            try:
                price = Decimal(row["Retail Price"]).quantize(Decimal("0.001"))
            except (InvalidOperation, TypeError):
                raise CommandError(f"Line {line}: bad price")
            external_id = (row["OPIS Truckstop ID"] or "").strip()
            if external_id in cheapest and Decimal(cheapest[external_id][1]["price"]) <= price:
                continue
            cheapest[external_id] = (line, {
                "id": external_id,
                "name": row["Truckstop Name"],
                "address": f"{row['Address'].strip()}, {place['name']}",
                "latitude": str(place["latitude"]),
                "longitude": str(place["longitude"]),
                "price": str(price),
            })
        return list(cheapest.values()), skipped

    def parse_row(self, row, seen_ids):
        external_id = (row["id"] or "").strip()
        name = (row["name"] or "").strip()
        address = (row.get("address") or "").strip()
        if not external_id or len(external_id) > 100:
            raise ValueError("bad id")
        if external_id in seen_ids:
            raise ValueError(f"duplicate id {external_id}")
        if not name or len(name) > 200:
            raise ValueError("bad name")
        if len(address) > 300:
            raise ValueError("address too long")

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("coordinates out of range")

        try:
            price = Decimal(row["price"])
        except (InvalidOperation, TypeError):
            raise ValueError("bad price")
        if not price.is_finite() or price <= 0 or price >= 1000:
            raise ValueError("bad price")
        if price != price.quantize(Decimal("0.001")):
            raise ValueError("price has more than 3 decimals")

        seen_ids.add(external_id)
        return Station(
            external_id=external_id,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            price=price,
        )
