from rest_framework.views import APIView
from rest_framework.response import Response

from common.responses import error_response
from common.exceptions import AppError
from .models import Ticket
from .serializers import (
    TicketCreateSerializer,
    TicketListItemSerializer,
    TicketStatusUpdateSerializer,
)
from .services import claim_ticket, change_status


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

        ticket = Ticket.objects.create(
            created_by=request.user,
            title=data["title"],
            description=data["description"],
            priority=data.get("priority", "medium"),
        )

        return Response(TicketListItemSerializer(ticket).data, status=201)


class TicketListView(APIView):
    """
    GET /api/tickets?page=1&page_size=10
    - client => faqat o'ziniki
    - agent/admin => hammasi (keyin filter qo'shamiz)
    """
    def get(self, request):
        qs = Ticket.objects.select_related("created_by", "assigned_to").order_by("-created_at")

        if request.user.role == "client":
            qs = qs.filter(created_by=request.user)

        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "10"))
        start = (page - 1) * page_size
        end = start + page_size

        items = qs[start:end]

        return Response(
            {
                "page": page,
                "page_size": page_size,
                "count": qs.count(),
                "results": TicketListItemSerializer(items, many=True).data,
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