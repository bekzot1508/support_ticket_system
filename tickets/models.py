import uuid
from django.db import models
from django.conf import settings


class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class Ticket(models.Model):
    """
    Core entity.
    Middle signal:
    - assigned_to nullable (claim/assign flow)
    - status flow (open -> in_progress -> resolved -> closed)
    - resolved_at separate field (reporting uchun)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tickets",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=180)
    description = models.TextField()

    priority = models.CharField(
        max_length=16, choices=TicketPriority.choices, default=TicketPriority.MEDIUM
    )
    status = models.CharField(
        max_length=16, choices=TicketStatus.choices, default=TicketStatus.OPEN
    )

    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TicketMessage(models.Model):
    """
    Ticket ichidagi muloqot.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class TicketHistory(models.Model):
    """
    Audit log: kim nima o'zgartirdi.
    Senior vibe: write operations "history" ga yoziladi.

    field: status / assigned_to / priority
    old_value/new_value: string (oddiy va audit uchun yetarli)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    field = models.CharField(max_length=32)
    old_value = models.CharField(max_length=255, blank=True, default="")
    new_value = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)