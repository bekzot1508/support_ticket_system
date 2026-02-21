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
            "created_at",
            "updated_at",
        ]


class TicketStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TicketStatus.values)