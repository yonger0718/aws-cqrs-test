# Query Service EKS Handler
# CQRS + Hexagonal Architecture Implementation

from .main import LambdaAdapter, NotificationRecord, QueryPort, QueryResult, QueryService, app

__version__ = "2.0.0"
__all__ = ["NotificationRecord", "QueryResult", "QueryPort", "QueryService", "LambdaAdapter", "app"]
