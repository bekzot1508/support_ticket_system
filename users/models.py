import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class UserRole(models.TextChoices):
    CLIENT = "client", "Client"
    AGENT = "agent", "Agent"
    ADMIN = "admin", "Admin"


class User(AbstractUser):
    """
    Senior-vibe:
    - UUID primary key (distributed systems mindset)
    - role = RBAC light (client/agent/admin)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.CLIENT)
