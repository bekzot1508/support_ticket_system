from rest_framework.views import APIView
from rest_framework.response import Response

from common.responses import error_response
from common.exceptions import AppError
from common.pagination import paginate_queryset
from .models import Ticket, NotificationOutbox
from .serializers import (
    TicketCreateSerializer,
    TicketListItemSerializer,
    TicketStatusUpdateSerializer,
    TicketDetailSerializer,
    MessageCreateSerializer,
    TicketMessageSerializer,
    TicketAssignSerializer,
    NotificationListSerializer,
    NotificationAckSerializer,
)
from .permissions import CanViewTicket, CanWriteTicket, IsAgentOrAdmin, IsNotificationOwner
from .services import add_message, claim_ticket, change_status, create_ticket, mark_sla_breached_if_needed, \
    assign_ticket, acknowledge_notification
from .selectors import tickets_qs, apply_ticket_filters, agent_queue_qs, notifications_qs




class TicketCreateView(APIView):
    """
    POST /api/tickets
    Client ticket ochadi.
    """
    def post(self, request):
        ser = TicketCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": ser.errors}},
                status=400,
            )

        data = ser.validated_data

        try:
            ticket = create_ticket(
                actor=request.user,
                title=data["title"],
                description=data["description"],
                priority=data.get("priority", "medium"),
            )
        except AppError as e:
            return error_response(e)

        return Response(TicketListItemSerializer(ticket).data, status=201)


class TicketListView(APIView):
    """
    GET /api/tickets?status=open&priority=high&page=1&page_size=10
    """

    def get(self, request):
        qs = tickets_qs().order_by("-created_at")

        # RBAC: client faqat o'ziniki
        if request.user.role == "client":
            qs = qs.filter(created_by=request.user)

        # filters
        qs = apply_ticket_filters(qs, request.query_params)

        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "10"))
        data = paginate_queryset(qs, page=page, page_size=page_size)

        return Response(
            {
                "page": data["page"],
                "page_size": data["page_size"],
                "count": data["count"],
                "results": TicketListItemSerializer(data["results"], many=True).data,
            }
        )


class TicketClaimView(APIView):
    """
    POST /api/tickets/{id}/claim
    Agent ticketni claim qiladi (transaction + select_for_update).
    """
    def post(self, request, ticket_id):
        try:
            ticket = claim_ticket(ticket_id=ticket_id, actor=request.user)
        except AppError as e:
            return error_response(e)

        return Response(TicketListItemSerializer(ticket).data, status=200)


class TicketStatusView(APIView):
    """
    PATCH /api/tickets/{id}/status
    Body: { "status": "resolved" }
    """
    def patch(self, request, ticket_id):
        ser = TicketStatusUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": ser.errors}},
                status=400,
            )

        try:
            ticket = change_status(
                ticket_id=ticket_id,
                actor=request.user,
                new_status=ser.validated_data["status"],
            )
        except AppError as e:
            return error_response(e)

        return Response(TicketListItemSerializer(ticket).data, status=200)


#==========================
# second adding
#==========================
class TicketDetailView(APIView):
    """
    GET /api/tickets/{id}
    - client faqat o'ziniki
    - agent/admin hammasi
    """
    def get(self, request, ticket_id):
        ticket = Ticket.objects.select_related("created_by", "assigned_to") \
            .prefetch_related("messages", "history") \
            .get(id=ticket_id)

        # object permission
        perm = CanViewTicket()
        if not perm.has_object_permission(request, self, ticket):
            return Response({"error": {"code": "PERMISSION_DENIED", "message": "Forbidden", "details": {}}}, status=403)

        return Response(TicketDetailSerializer(ticket).data)


class TicketMessageCreateView(APIView):
    """
    POST /api/tickets/{id}/messages
    Body: { "body": "..." }

    - client: faqat o'z ticketiga
    - agent/admin: hammasiga
    """
    def post(self, request, ticket_id):
        ser = MessageCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": ser.errors}},
                status=400,
            )

        ticket = Ticket.objects.get(id=ticket_id)

        perm = CanWriteTicket()
        if not perm.has_object_permission(request, self, ticket):
            return Response({"error": {"code": "PERMISSION_DENIED", "message": "Forbidden", "details": {}}}, status=403)

        try:
            msg = add_message(ticket_id=ticket_id, actor=request.user, body=ser.validated_data["body"])
        except AppError as e:
            return error_response(e)

        return Response(TicketMessageSerializer(msg).data, status=201)


# new
class AgentQueueView(APIView):
    """
    GET /api/agent/queue?status=open&page=1&page_size=10

    - faqat agent/admin
    - default: status=open (work queue)
    - overdue first ordering
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        qs = tickets_qs()

        status = request.query_params.get("status", "open")
        if status:
            qs = qs.filter(status=status)

        qs = apply_ticket_filters(qs, request.query_params)
        qs = agent_queue_qs(qs)

        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "10"))
        data = paginate_queryset(qs, page=page, page_size=page_size)

        # Side-effect: SLA breached audit (only for visible page items)
        for t in data["results"]:
            mark_sla_breached_if_needed(ticket=t, actor=request.user)

        return Response(
            {
                "page": data["page"],
                "page_size": data["page_size"],
                "count": data["count"],
                "results": TicketListItemSerializer(data["results"], many=True).data,
            }
        )


# new
class TicketAssignView(APIView):
    """
    POST /api/tickets/{id}/assign
    Body:
      { "agent_id": "<uuid>" }

    Faqat admin.
    """
    def post(self, request, ticket_id):
        ser = TicketAssignSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": ser.errors}},
                status=400,
            )

        try:
            ticket = assign_ticket(
                ticket_id=ticket_id,
                actor=request.user,
                agent_id=ser.validated_data["agent_id"],
            )
        except AppError as e:
            return error_response(e)

        return Response(TicketListItemSerializer(ticket).data, status=200)


class NotificationListView(APIView):
    """
    GET /api/notifications?status=sent&page=1&page_size=20

    - faqat o'z notificationlari
    - filter: status (pending/sent/failed)
    """
    def get(self, request):
        qs = notifications_qs().filter(to_user=request.user).order_by("-created_at")

        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "20"))
        data = paginate_queryset(qs, page=page, page_size=page_size)

        return Response({
            "page": data["page"],
            "page_size": data["page_size"],
            "count": data["count"],
            "results": NotificationListSerializer(data["results"], many=True).data,
        })


class NotificationDetailView(APIView):
    """
    GET /api/notifications/{id}
    """
    def get(self, request, notification_id):
        n = NotificationOutbox.objects.select_related("to_user").get(id=notification_id)

        perm = IsNotificationOwner()
        if not perm.has_object_permission(request, self, n):
            return Response({"error": {"code": "PERMISSION_DENIED", "message": "Forbidden", "details": {}}}, status=403)

        return Response(NotificationListSerializer(n).data)


class NotificationAckView(APIView):
    """
    POST /api/notifications/{id}/ack
    - read_at set qiladi
    """
    def post(self, request, notification_id):
        # body bo‘sh bo‘lishi mumkin
        ser = NotificationAckSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": ser.errors}},
                status=400,
            )

        n = NotificationOutbox.objects.get(id=notification_id)

        perm = IsNotificationOwner()
        if not perm.has_object_permission(request, self, n):
            return Response({"error": {"code": "PERMISSION_DENIED", "message": "Forbidden", "details": {}}}, status=403)

        try:
            acknowledge_notification(notification=n, actor=request.user)
        except AppError as e:
            return error_response(e)

        n.refresh_from_db()
        return Response(NotificationListSerializer(n).data, status=200)