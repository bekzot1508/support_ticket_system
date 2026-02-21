from django.contrib import admin
from .models import Ticket, TicketMessage, TicketHistory


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "created_by__username", "assigned_to__username")
    ordering = ("-created_at",)


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("ticket__title", "author__username", "body")
    ordering = ("-created_at",)


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "actor", "field", "old_value", "new_value", "created_at")
    list_filter = ("field",)
    ordering = ("-created_at",)