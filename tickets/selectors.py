from django.db.models import QuerySet, Case, When, Value, BooleanField
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import Ticket


def tickets_qs() -> QuerySet:
    # N+1 oldini olish: FK larni oldindan olib qo‘yamiz
    return Ticket.objects.select_related("created_by", "assigned_to")


def apply_ticket_filters(qs: QuerySet, params) -> QuerySet:
    """
    params = request.query_params

    Supported:
      status, priority, assigned_to, created_by,
      created_from, created_to (ISO datetime)
    """
    status = params.get("status")
    priority = params.get("priority")
    assigned_to = params.get("assigned_to")
    created_by = params.get("created_by")
    created_from = params.get("created_from")
    created_to = params.get("created_to")

    if status:
        qs = qs.filter(status=status)

    if priority:
        qs = qs.filter(priority=priority)

    if assigned_to:
        qs = qs.filter(assigned_to_id=assigned_to)

    if created_by:
        qs = qs.filter(created_by_id=created_by)

    # Date range (ISO)
    if created_from:
        dt = parse_datetime(created_from)
        if dt:
            qs = qs.filter(created_at__gte=dt)

    if created_to:
        dt = parse_datetime(created_to)
        if dt:
            qs = qs.filter(created_at__lte=dt)

    return qs


#==========================
# second adding
#==========================
def agent_queue_qs(qs: QuerySet) -> QuerySet:
    """
    Queue ordering:
      1) OPEN va overdue bo'lganlar tepada
      2) due_at eng yaqin
      3) created_at eskiroq (FIFO vibe)
    """
    now = timezone.now()

    # overdue flag annotate (DB level sorting)
    qs = qs.annotate(
        is_overdue=Case(
            When(due_at__isnull=False, due_at__lt=now, status="open", then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    return qs.order_by("-is_overdue", "due_at", "created_at")