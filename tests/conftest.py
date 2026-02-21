import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.fixture
def api():
    return APIClient()

@pytest.fixture
def client_user(db):
    return User.objects.create_user(username="client1", password="pass1234", role="client")

@pytest.fixture
def agent_user(db):
    return User.objects.create_user(username="agent1", password="pass1234", role="agent")