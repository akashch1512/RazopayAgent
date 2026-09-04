# Import every ORM model here so that `Base.metadata` is fully populated
# for Alembic autogenerate and metadata-based table creation.
from src.models.db.business import Business  # noqa: F401, E402
from src.models.db.webhook_event import WebhookEvent  # noqa: F401, E402
from src.repository.table import Base

__all__ = ["Base"]
