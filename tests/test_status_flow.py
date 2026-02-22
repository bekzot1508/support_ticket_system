import pytest
from tickets.models import Ticket

@pytest.mark.django_db
def test_invalid_status_transition(api, client_user, agent_user):
    ticket = Ticket.objects.create(
        created_by=client_user,
        title="Flow test",
        description="x",
        status="open"
    )

    api.force_authenticate(user=agent_user)

    # open -> resolved (invalid)
    res = api.patch(
        f"/api/tickets/{ticket.id}/status/",
        {"status": "resolved"},
        format="json"
    )

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"
    assert "Invalid status transition" in res.json()["error"]["message"]