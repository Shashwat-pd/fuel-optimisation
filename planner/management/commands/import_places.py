import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.models import Place
from planner.places import make_key

DEFAULT_FILE = Path(settings.BASE_DIR) / "data" / "places.csv"


class Command(BaseCommand):
    help = "Load the US city list used to look up start, finish and station cities."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", nargs="?", default=str(DEFAULT_FILE))

    def handle(self, *args, **options):
        places = {}
        try:
            with open(options["csv_path"], newline="") as f:
                for row in csv.DictReader(f):
                    state, key = make_key(row["name"], row["state"])
                    places[(state, key)] = Place(
                        state=state,
                        key=key,
                        name=f"{row['name']}, {row['state']}",
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                    )
        except OSError as e:
            raise CommandError(str(e))
        except (KeyError, ValueError) as e:
            raise CommandError(f"Bad places file: {e}")
        if not places:
            raise CommandError("Places file is empty; existing places were kept.")

        with transaction.atomic():
            Place.objects.all().delete()
            Place.objects.bulk_create(places.values(), batch_size=5000)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(places)} places."))
