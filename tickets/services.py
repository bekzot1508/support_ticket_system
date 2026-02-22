# Services: transaction + select_for_update (race condition killer)

from django.db import transaction
from django.utils import timezone

from common.exceptions import ConflictError, PermissionDenied, NotFoundError
from users.models import UserRole
from .models import Ticket, TicketHistory, TicketStatus, TicketMessage, NotificationOutbox, NotificationStatus
from .constants import ALLOWED_STATUS_TRANSITIONS, SLA_BY_PRIORITY
from django.contrib.auth import get_user_model
from django.db.models import F


User = get_user_model()


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


# yangilangan change status
@transaction.atomic
def change_status(*, ticket_id, actor, new_status: str) -> Ticket:
    """
    Status change with strict flow validation.

    Business rules:
      - Transition only if allowed
      - RESOLVED/CLOSED faqat agent/admin
    """
    try:
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise NotFoundError("Ticket not found")

    current_status = ticket.status

    # 1️⃣ Flow validation
    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_next:
        raise ConflictError(
            f"Invalid status transition: {current_status} -> {new_status}",
            details={"allowed": list(allowed_next)},
        )

    # 2️⃣ Role-based rule
    if new_status == TicketStatus.RESOLVED and actor.role not in ["agent", "admin"]:
        raise PermissionDenied("Only agent/admin can resolve tickets")

    if new_status == TicketStatus.CLOSED and actor.role not in ["agent", "admin"]:
        raise PermissionDenied("Only agent/admin can close tickets")

    old_status = ticket.status
    ticket.status = new_status

    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = timezone.now()

    if new_status == TicketStatus.RESOLVED:
        enqueue_notification(
            to_user=ticket.created_by,
            event="ticket_resolved",
            payload={
                "ticket_id": str(ticket.id),
                "title": ticket.title,
            },
        )

    ticket.save(update_fields=["status", "resolved_at", "updated_at"])


    _history(ticket=ticket, actor=actor, field="status", old=old_status, new=new_status)

    return ticket


# previous change status
# @transaction.atomic
# def change_status(*, ticket_id, actor, new_status: str) -> Ticket:
#     """
#     Status change.
#     Business rule:
#       - RESOLVED faqat agent/admin qila oladi
#       - CLOSED ham agent/admin (soddalashtiramiz)
#     """
#     try:
#         ticket = Ticket.objects.select_for_update().get(id=ticket_id)
#     except Ticket.DoesNotExist:
#         raise NotFoundError("Ticket not found")
#
#     if new_status == TicketStatus.RESOLVED and actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
#         raise PermissionDenied("Only agent/admin can resolve tickets")
#
#     if new_status == TicketStatus.CLOSED and actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
#         raise PermissionDenied("Only agent/admin can close tickets")
#
#     old_status = ticket.status
#     ticket.status = new_status
#
#     if new_status == TicketStatus.RESOLVED:
#         ticket.resolved_at = timezone.now()
#
#     ticket.save(update_fields=["status", "resolved_at", "updated_at"])
#     _history(ticket=ticket, actor=actor, field="status", old=old_status, new=new_status)
#
#     return ticket


#==========================
# second adding
#==========================
@transaction.atomic
def add_message(*, ticket_id, actor, body: str) -> TicketMessage:
    """
    Har message ticket history emas, lekin message record — auditning o‘zi.
    Xohlasang historyga ham "message" event yozsa bo‘ladi.
    """
    try:
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise NotFoundError("Ticket not found")

    msg = TicketMessage.objects.create(ticket=ticket, author=actor, body=body)
    return msg

# new
@transaction.atomic
def create_ticket(*, actor, title: str, description: str, priority: str) -> Ticket:
    """
    Ticket creation:
    - due_at SLA bilan hisoblanadi
    - (xohlasang) create event historyga yozish mumkin
    """
    from django.utils import timezone

    delta = SLA_BY_PRIORITY.get(priority)
    due_at = timezone.now() + delta if delta else None

    ticket = Ticket.objects.create(
        created_by=actor,
        title=title,
        description=description,
        priority=priority,
        due_at=due_at,
    )

    # Notify all agents (simple). Real systemda: team/queue bo‘yicha target qilinadi.
    from django.contrib.auth import get_user_model
    User = get_user_model()
    agents = User.objects.filter(role="agent", is_active=True)

    for a in agents:
        enqueue_notification(
            to_user=a,
            event="ticket_created",
            payload={
                "ticket_id": str(ticket.id),
                "title": ticket.title,
                "priority": ticket.priority,
            },
        )
    return ticket


# new
@transaction.atomic
def mark_sla_breached_if_needed(*, ticket: Ticket, actor) -> None:
    """
    Overdue bo‘lsa, historyga 1 marta yozamiz.
    field = "sla"
    new_value = "breached"
    """
    from django.utils import timezone

    if ticket.status != "open" or not ticket.due_at:
        return

    if ticket.due_at >= timezone.now():
        return

    exists = TicketHistory.objects.filter(ticket=ticket, field="sla", new_value="breached").exists()
    if exists:
        return

    TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        field="sla",
        old_value="",
        new_value="breached",
    )


# new
@transaction.atomic
def assign_ticket(*, ticket_id, actor, agent_id):
    """
    Admin agentga assign qiladi.

    - Faqat admin
    - agent_id roli agent bo‘lishi kerak
    - history yoziladi
    """
    if actor.role != "admin":
        raise PermissionDenied("Only admin can assign tickets")

    try:
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise NotFoundError("Ticket not found")

    try:
        agent = User.objects.get(id=agent_id)
    except User.DoesNotExist:
        raise NotFoundError("Agent not found")

    if agent.role != "agent":
        raise ConflictError("Assigned user must have agent role")

    old_assigned = ticket.assigned_to_id
    old_status = ticket.status

    ticket.assigned_to = agent

    # Agar hali open bo‘lsa, in_progress qilamiz
    if ticket.status == "open":
        ticket.status = "in_progress"

    ticket.save(update_fields=["assigned_to", "status", "updated_at"])

    _history(ticket=ticket, actor=actor, field="assigned_to", old=old_assigned, new=agent.id)

    if old_status != ticket.status:
        _history(ticket=ticket, actor=actor, field="status", old=old_status, new=ticket.status)

    return ticket


def enqueue_notification(*, to_user, event: str, payload: dict) -> None:
    """
    DB outboxga yozib qo‘yamiz.
    Side-effect safe: request ichida tez, tashqi servisga bog‘liq emas.
    """
    NotificationOutbox.objects.create(
        to_user=to_user,
        event=event,
        payload=payload,
    )


@transaction.atomic
def process_outbox_batch(*, limit: int = 50) -> int:
    """
    Pending notificationlarni batch qilib "send" qiladi.
    select_for_update(skip_locked=True) -> parallel workerlar bo‘lsa ham safe.

    Bu yerda real email yubormaymiz.
    Production'da bu joyga provider (SES/Sendgrid) ulab qo‘yiladi.
    """
    from django.utils import timezone

    qs = (
        NotificationOutbox.objects
        .select_for_update(skip_locked=True)
        .filter(status=NotificationStatus.PENDING)
        .order_by("created_at")[:limit]
    )

    processed = 0
    for n in qs:
        try:
            # SIMULATION: "sent" deb belgilaymiz
            n.status = NotificationStatus.SENT
            n.sent_at = timezone.now()
            n.last_error = ""
            n.save(update_fields=["status", "sent_at", "last_error"])

            processed += 1
        except Exception as e:
            # Failure accounting (retryable)
            n.status = NotificationStatus.FAILED
            n.attempts = F("attempts") + 1
            n.last_error = str(e)
            n.save(update_fields=["status", "attempts", "last_error"])

    return processed


from django.utils import timezone

@transaction.atomic
def acknowledge_notification(*, notification, actor):
    """
    Idempotent ack:
    - Agar oldin read bo‘lgan bo‘lsa qayta yozmaydi
    """
    if notification.to_user_id != actor.id:
        raise PermissionDenied("Cannot acknowledge чужой notification")

    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])