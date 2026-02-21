# Services: transaction + select_for_update (race condition killer)

from django.db import transaction
from django.utils import timezone

from common.exceptions import ConflictError, PermissionDenied, NotFoundError
from users.models import UserRole
from .models import Ticket, TicketHistory, TicketStatus


def _history(*, ticket, actor, field, old, new):
    """
    Audit helper: har muhim o'zgarish history ga yoziladi.
    """
    TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        field=field,
        old_value=str(old or ""),
        new_value=str(new or ""),
    )


@transaction.atomic
def claim_ticket(*, ticket_id, actor) -> Ticket:
    """
    Agent ticketni o'ziga "claim" qiladi.
    Middle signal: race condition'ni DB row lock bilan yopamiz.

    SELECT ... FOR UPDATE:
    - Shu ticket row lock bo'ladi
    - 2 agent parallel claim qilsa:
      bittasi birinchi oladi, ikkinchisi lockdan keyin "already claimed" oladi.
    """
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise PermissionDenied("Only agent/admin can claim tickets")

    try:
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise NotFoundError("Ticket not found")

    if ticket.assigned_to_id is not None:
        raise ConflictError(
            "Ticket already claimed",
            details={"assigned_to": str(ticket.assigned_to_id)},
        )

    old_assigned = ticket.assigned_to_id
    old_status = ticket.status

    ticket.assigned_to = actor
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.save(update_fields=["assigned_to", "status", "updated_at"])

    _history(ticket=ticket, actor=actor, field="assigned_to", old=old_assigned, new=actor.id)
    _history(ticket=ticket, actor=actor, field="status", old=old_status, new=ticket.status)

    return ticket


@transaction.atomic
def change_status(*, ticket_id, actor, new_status: str) -> Ticket:
    """
    Status change.
    Business rule:
      - RESOLVED faqat agent/admin qila oladi
      - CLOSED ham agent/admin (soddalashtiramiz)
    """
    try:
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise NotFoundError("Ticket not found")

    if new_status == TicketStatus.RESOLVED and actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise PermissionDenied("Only agent/admin can resolve tickets")

    if new_status == TicketStatus.CLOSED and actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise PermissionDenied("Only agent/admin can close tickets")

    old_status = ticket.status
    ticket.status = new_status

    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = timezone.now()

    ticket.save(update_fields=["status", "resolved_at", "updated_at"])
    _history(ticket=ticket, actor=actor, field="status", old=old_status, new=new_status)

    return ticket