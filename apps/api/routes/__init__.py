from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.repos import router as repos_router
from api.routes.settings import router as settings_router

__all__ = ["auth_router", "health_router", "jobs_router", "repos_router", "settings_router"]
