from rest_framework.permissions import BasePermission


class IsClient(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "client"


class IsAgentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in ["agent", "admin"]


class CanViewTicket(BasePermission):
    """
    Ticket view rule:
      - admin: hammasi
      - agent: hammasi (yoki faqat assigned ham qilsa bo‘ladi — biz hozir hammasi deymiz)
      - client: faqat o‘ziniki
    """
    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", None)
        if role == "admin":
            return True
        if role == "agent":
            return True
        return obj.created_by_id == request.user.id


class CanWriteTicket(BasePermission):
    """
    Ticket write rule:
      - admin: hammasi
      - agent: status change, message, claim (bizda endpointlar shunday)
      - client: faqat o‘z ticketiga message yozishi mumkin, status/claim qila olmaydi
    """
    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", None)
        if role == "admin":
            return True
        if role == "agent":
            return True
        return obj.created_by_id == request.user.id


class IsNotificationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.to_user_id == request.user.id