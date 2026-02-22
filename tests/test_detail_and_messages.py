import pytest
from tickets.models import Ticket

@pytest.mark.django_db
def test_client_cannot_view_others_ticket(api, client_user, agent_user):
    # ticket created by agent_user (not client_user)
    ticket = Ticket.objects.create(created_by=agent_user, title="Private", description="x")

    api.force_authenticate(user=client_user)
    res = api.get(f"/api/tickets/{ticket.id}/")

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"

@pytest.mark.django_db
def test_client_can_write_message_on_own_ticket(api, client_user):
    ticket = Ticket.objects.create(created_by=client_user, title="Hello", description="x")

    api.force_authenticate(user=client_user)
    res = api.post(f"/api/tickets/{ticket.id}/messages/", {"body": "Please help"}, format="json")

    assert res.status_code == 201
    assert res.json()["body"] == "Please help"

@pytest.mark.django_db
def test_filtering_by_status(api, client_user, agent_user):
    t1 = Ticket.objects.create(created_by=client_user, title="A", description="x", status="open")
    t2 = Ticket.objects.create(created_by=client_user, title="B", description="x", status="in_progress")

    api.force_authenticate(user=agent_user)
    res = api.get("/api/tickets/?status=open")

    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["results"]]
    assert str(t1.id) in ids
    assert str(t2.id) not in ids