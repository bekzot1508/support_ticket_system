from typing import Any, Dict
from django.db.models import QuerySet


def paginate_queryset(qs: QuerySet, *, page: int, page_size: int) -> Dict[str, Any]:
    """
    Simple, explicit pagination (DRF paginator ishlatmaymiz — tushunish oson bo‘lsin).

    Returns:
      {
        "page": 1,
        "page_size": 10,
        "count": 123,
        "results": <slice queryset>
      }
    """
    page = max(1, int(page))
    page_size = min(100, max(1, int(page_size)))  # hard limit: 100

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "page": page,
        "page_size": page_size,
        "count": qs.count(),
        "results": qs[start:end],
    }