import csv

from django.core.management.base import BaseCommand

from planner.models import Station


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        with open(options["path"]) as f:
            for row in csv.DictReader(f):
                Station.objects.create(
                    name=row["name"],
                    address=row.get("address", ""),
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    price=row["price"],
                )
        self.stdout.write("done")
