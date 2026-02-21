from django.urls import path
from .views import TicketCreateView, TicketListView, TicketClaimView, TicketStatusView

urlpatterns = [
    path("tickets", TicketListView.as_view()),
    path("tickets/create", TicketCreateView.as_view()),  # xohlasang create ni /tickets ga birlashtiramiz keyin
    path("tickets/<uuid:ticket_id>/claim", TicketClaimView.as_view()),
    path("tickets/<uuid:ticket_id>/status", TicketStatusView.as_view()),
]