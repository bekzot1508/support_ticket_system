import pytest
from django.contrib.auth import get_user_model
from tickets.models import Ticket

User = get_user_model()

@pytest.mark.django_db
def test_admin_can_assign_ticket(api, client_user, agent_user):
    admin = User.objects.create_user(
        username="admin1",
        password="pass1234",
        role="admin",
    )

    ticket = Ticket.objects.create(
        created_by=client_user,
        title="Assign test",
        description="x",
        status="open",
    )

    api.force_authenticate(user=admin)
    res = api.post(
        f"/api/tickets/{ticket.id}/assign/",
        {"agent_id": str(agent_user.id)},
        format="json",
    )

    assert res.status_code == 200
    ticket.refresh_from_db()
    assert ticket.assigned_to_id == agent_user.id
    assert ticket.status == "in_progress"


@pytest.mark.django_db
def test_non_admin_cannot_assign(api, client_user, agent_user):
    ticket = Ticket.objects.create(
        created_by=client_user,
        title="Assign test",
        description="x",
        status="open",
    )

    api.force_authenticate(user=agent_user)
    res = api.post(
        f"/api/tickets/{ticket.id}/assign/",
        {"agent_id": str(agent_user.id)},
        format="json",
    )

    assert res.status_code == 403