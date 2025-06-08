# Query Service ECS Handler
# CQRS + Hexagonal Architecture Implementation

from .main import InternalAPIAdapter, NotificationRecord, QueryPort, QueryResult, QueryService, app

__version__ = "3.0.0"
__all__ = [
    "NotificationRecord",
    "QueryResult",
    "QueryPort",
    "QueryService",
    "InternalAPIAdapter",
    "app",
]
