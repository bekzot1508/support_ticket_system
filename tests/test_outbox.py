import pytest
from django.contrib.auth import get_user_model
from tickets.models import Ticket, NotificationOutbox, NotificationStatus

User = get_user_model()

@pytest.mark.django_db
def test_ticket_create_enqueues_notification_for_agents(api, client_user, agent_user):
    api.force_authenticate(user=client_user)

    res = api.post(
        "/api/tickets/create/",
        {"title": "Notify", "description": "x", "priority": "high"},
        format="json",
    )
    assert res.status_code == 201

    # agent uchun outbox yozilgan bo‘lishi kerak
    assert NotificationOutbox.objects.filter(
        to_user=agent_user,
        event="ticket_created",
        status=NotificationStatus.PENDING,
    ).exists()

@pytest.mark.django_db
def test_process_outbox_marks_sent(db, client_user, agent_user):
    # outboxga qo‘lbola yozamiz
    n = NotificationOutbox.objects.create(
        to_user=agent_user,
        event="ticket_created",
        payload={"x": 1},
    )
    assert n.status == NotificationStatus.PENDING

    from tickets.services import process_outbox_batch
    processed = process_outbox_batch(limit=10)
    assert processed == 1

    n.refresh_from_db()
    assert n.status == NotificationStatus.SENT
    assert n.sent_at is not None