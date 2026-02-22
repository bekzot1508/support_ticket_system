from datetime import timedelta
from .models import TicketStatus, TicketPriority

# Allowed transitions graph
ALLOWED_STATUS_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED},
    TicketStatus.CLOSED: set(),  # terminal state
}


#==========================
# second adding
#==========================
# SLA policy (realistic, interview-friendly)
SLA_BY_PRIORITY = {
    TicketPriority.URGENT: timedelta(minutes=15),
    TicketPriority.HIGH: timedelta(hours=2),
    TicketPriority.MEDIUM: timedelta(hours=8),
    TicketPriority.LOW: timedelta(hours=24),
}