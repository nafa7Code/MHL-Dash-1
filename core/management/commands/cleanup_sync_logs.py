from django.core.management.base import BaseCommand
from core.models import SyncLog
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Delete completed sync logs older than 5 minutes"

    def handle(self, *args, **kwargs):
        threshold = timezone.now() - timedelta(minutes=5)
        deleted, _ = SyncLog.objects.filter(
            completed=True, updated_at__lt=threshold).delete()
        self.stdout.write(self.style.SUCCESS(
            f"🧹 Deleted {deleted} old sync logs."))
