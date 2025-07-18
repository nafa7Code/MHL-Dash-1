from django.utils.timezone import now
from core.models import SyncStatus


def update_last_sync(key: str):
    SyncStatus.objects.update_or_create(
        key=key,
        defaults={"last_synced_at": now()}
    )
