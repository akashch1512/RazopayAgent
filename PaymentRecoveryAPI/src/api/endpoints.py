import fastapi

from src.api.routes.business_recovery_cases import router as business_recovery_cases_router
from src.api.routes.businesses import router as businesses_router
from src.api.routes.invoices import router as invoices_router
from src.api.routes.razorpay import router as razorpay_router
from src.api.routes.recovery_cases import router as recovery_cases_router
from src.api.routes.webhook_events import router as webhook_events_router
from src.api.routes.webhooks import router as webhooks_router

router = fastapi.APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(router=businesses_router)
router.include_router(router=invoices_router)
router.include_router(router=business_recovery_cases_router)
router.include_router(router=recovery_cases_router)
router.include_router(router=razorpay_router)
router.include_router(router=webhook_events_router)
router.include_router(router=webhooks_router)
