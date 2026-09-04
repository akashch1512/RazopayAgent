import fastapi

from src.api.routes.onboarding import router as onboarding_router
from src.api.routes.webhooks import router as webhooks_router

router = fastapi.APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(router=onboarding_router)
router.include_router(router=webhooks_router)
