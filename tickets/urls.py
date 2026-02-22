from django.urls import path
from .views import (
    TicketCreateView,
    TicketListView,
    TicketClaimView,
    TicketStatusView,
    TicketDetailView,
    TicketMessageCreateView,
    AgentQueueView,
    TicketAssignView,
)

urlpatterns = [
    path("tickets/", TicketListView.as_view()),
    path("tickets/create/", TicketCreateView.as_view()),

    path("tickets/<uuid:ticket_id>/", TicketDetailView.as_view()),
    path("tickets/<uuid:ticket_id>/messages/", TicketMessageCreateView.as_view()),

    path("tickets/<uuid:ticket_id>/claim/", TicketClaimView.as_view()),
    path("tickets/<uuid:ticket_id>/status/", TicketStatusView.as_view()),

    path("agent/queue/", AgentQueueView.as_view()),

    path("tickets/<uuid:ticket_id>/assign/", TicketAssignView.as_view()),
]