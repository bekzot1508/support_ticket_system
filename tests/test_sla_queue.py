import pytest
from django.utils import timezone
from datetime import timedelta

from tickets.models import Ticket

@pytest.mark.django_db
def test_ticket_create_sets_due_at(api, client_user):
    api.force_authenticate(user=client_user)

    res = api.post(
        "/api/tickets/create/",
        {"title": "SLA", "description": "x", "priority": "urgent"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["due_at"] is not None

@pytest.mark.django_db
def test_agent_queue_requires_agent(api, client_user):
    api.force_authenticate(user=client_user)
    res = api.get("/api/agent/queue/")
    assert res.status_code == 403

@pytest.mark.django_db
def test_agent_queue_orders_overdue_first(api, client_user, agent_user):
    now = timezone.now()

    # overdue ticket
    t1 = Ticket.objects.create(
        created_by=client_user,
        title="Overdue",
        description="x",
        status="open",
        due_at=now - timedelta(minutes=1),
    )
    # not overdue ticket
    t2 = Ticket.objects.create(
        created_by=client_user,
        title="Not overdue",
        description="x",
        status="open",
        due_at=now + timedelta(hours=1),
    )

    api.force_authenticate(user=agent_user)
    res = api.get("/api/agent/queue/?status=open")
    assert res.status_code == 200

    results = res.json()["results"]
    assert results[0]["id"] == str(t1.id)