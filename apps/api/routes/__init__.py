from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.settings import router as settings_router

__all__ = ["health_router", "jobs_router", "settings_router"]
