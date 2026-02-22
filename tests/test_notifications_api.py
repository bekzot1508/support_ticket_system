import pytest
from tickets.models import NotificationOutbox

@pytest.mark.django_db
def test_user_sees_only_own_notifications(api, client_user, agent_user):
    n1 = NotificationOutbox.objects.create(to_user=client_user, event="x", payload={})
    n2 = NotificationOutbox.objects.create(to_user=agent_user, event="y", payload={})

    api.force_authenticate(user=client_user)
    res = api.get("/api/notifications/")
    assert res.status_code == 200

    ids = [x["id"] for x in res.json()["results"]]
    assert str(n1.id) in ids
    assert str(n2.id) not in ids

@pytest.mark.django_db
def test_ack_sets_read_at(api, client_user):
    n = NotificationOutbox.objects.create(to_user=client_user, event="x", payload={})

    api.force_authenticate(user=client_user)
    res = api.post(f"/api/notifications/{n.id}/ack/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["read_at"] is not None

@pytest.mark.django_db
def test_cannot_ack_others_notification(api, client_user, agent_user):
    n = NotificationOutbox.objects.create(to_user=agent_user, event="x", payload={})

    api.force_authenticate(user=client_user)
    res = api.post(f"/api/notifications/{n.id}/ack/", {}, format="json")
    assert res.status_code == 403