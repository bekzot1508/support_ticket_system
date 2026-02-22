import pytest
from tickets.models import Ticket, TicketStatus

@pytest.mark.django_db
def test_agent_can_claim_ticket(api, client_user, agent_user):
    ticket = Ticket.objects.create(created_by=client_user, title="Bug", description="x")

    api.force_authenticate(user=agent_user)
    res = api.post(f"/api/tickets/{ticket.id}/claim/", format="json")

    assert res.status_code == 200
    ticket.refresh_from_db()
    assert ticket.assigned_to_id == agent_user.id
    assert ticket.status == TicketStatus.IN_PROGRESS

@pytest.mark.django_db
def test_ticket_cannot_be_claimed_twice(api, client_user, agent_user):
    ticket = Ticket.objects.create(created_by=client_user, title="Bug", description="x", assigned_to=agent_user)

    api.force_authenticate(user=agent_user)
    res = api.post(f"/api/tickets/{ticket.id}/claim/", format="json")

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"

@pytest.mark.django_db
def test_client_cannot_resolve_ticket(api, client_user):
    ticket = Ticket.objects.create(created_by=client_user, title="Pay", description="x")

    api.force_authenticate(user=client_user)
    res = api.patch(f"/api/tickets/{ticket.id}/status/", {"status": "resolved"}, format="json")

    assert res.status_code == 409  # 403 edi. 409 ga almashtirildi
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.OPEN