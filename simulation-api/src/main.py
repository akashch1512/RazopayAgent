"""
Demo stand-in for paid communication providers (SMS, WhatsApp, voice, email,
push) and the dashboard that shows what the recovery agent is doing, without
touching any real API or costing money. See `README.md`.

Two kinds of routes:
  * `/api/v1/simulate/*`  - called by the main backend's agent tools ("send a
    call/sms/whatsapp/email/app-notification"). Records the action.
  * `/api/v1/dashboard/*` - polled/posted by `frontend-demo` to show and react
    to what got recorded.
"""

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.app_notification import router as app_notification_router
from src.api.routes.call import router as call_router
from src.api.routes.email import router as email_router
from src.api.routes.meta import router as meta_router
from src.api.routes.sms import router as sms_router
from src.api.routes.whatsapp import router as whatsapp_router

app = fastapi.FastAPI(
    title="Recovery Agent Simulation API",
    description="Demo-only stand-in for paid comms providers - no real messages/calls are ever sent.",
)

# Wide open on purpose: this is a local demo service the Vite dev server talks
# to from a different origin, never a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
for router in (call_router, sms_router, whatsapp_router, email_router, app_notification_router, meta_router):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Recovery Agent Simulation API - demo only, no real messages are sent."}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
