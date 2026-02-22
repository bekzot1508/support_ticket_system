from django.core.management.base import BaseCommand
from tickets.services import process_outbox_batch


class Command(BaseCommand):
    help = "Process notification outbox (DB queue) and mark as sent."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        limit = options["limit"]
        processed = process_outbox_batch(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Processed: {processed} notifications"))