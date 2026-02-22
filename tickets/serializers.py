from rest_framework import serializers
from .models import Ticket, TicketMessage, TicketStatus, TicketPriority


class TicketCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField()
    priority = serializers.ChoiceField(choices=TicketPriority.values, required=False)


class TicketListItemSerializer(serializers.ModelSerializer):
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    assigned_to_id = serializers.UUIDField(source="assigned_to.id", read_only=True, allow_null=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "created_by_id",
            "assigned_to_id",
            "resolved_at",
            "due_at",
            "created_at",
            "updated_at",

        ]


class TicketStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TicketStatus.values)



from rest_framework import serializers
from .models import Ticket, TicketMessage, TicketHistory

# ... oldingi serializerlar qoladi


class TicketMessageSerializer(serializers.ModelSerializer):
    author_id = serializers.UUIDField(source="author.id", read_only=True)

    class Meta:
        model = TicketMessage
        fields = ["id", "author_id", "body", "created_at"]


class TicketHistorySerializer(serializers.ModelSerializer):
    actor_id = serializers.UUIDField(source="actor.id", read_only=True)

    class Meta:
        model = TicketHistory
        fields = ["id", "actor_id", "field", "old_value", "new_value", "created_at"]


#==========================
# second adding
#==========================
class TicketDetailSerializer(serializers.ModelSerializer):
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    assigned_to_id = serializers.UUIDField(source="assigned_to.id", read_only=True, allow_null=True)

    messages = TicketMessageSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "created_by_id",
            "assigned_to_id",
            "resolved_at",
            "due_at",
            "created_at",
            "updated_at",
            "messages",
            "history",
        ]


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField()

# new
class TicketAssignSerializer(serializers.Serializer):
    agent_id = serializers.UUIDField()