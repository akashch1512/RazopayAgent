# Recovery Agent Simulation API

Rather than integrating real (paid) communication APIs - SMS, WhatsApp, voice
calls, transactional email, push - this service fakes them for demo purposes.
It records what the recovery agent *would* have sent and serves that to
`../frontend-demo`, so the whole `webhook -> agent -> outreach action` flow is
visible end to end without spending money or needing real provider accounts.

No calling functionality is implemented - this is a recorder + dashboard feed,
not a telephony/messaging integration.

## Flow

```
backend agent tool  --POST /api/v1/simulate/<channel>-->  simulation-api  --stores in memory-->
                                                                 ^
frontend-demo  --GET/POST /api/v1/dashboard/users/{case_id}-----+
```

`{case_id}` is whatever the backend's `RecoveryCase.id` is - the agent tools
pass it automatically (via LangGraph's `InjectedState`, no LLM involvement).

## Run it

```bash
cd simulation-api
uv sync
uv run uvicorn src.app.main:app --reload --port 8001
```

Runs on **port 8090** (the main backend uses 8000, so they can run side by
side). Point the backend at it via `SIMULATION_API_BASE_URL` in the root
`.env` (defaults to `http://localhost:8090/api/v1`).

To point `frontend-demo` at it, set in its own `.env`:

```
VITE_API_BASE_URL=http://localhost:8090/api/v1
```

## Routes

- `POST /api/v1/simulate/{call,sms,whatsapp,email,app-notification}` - called
  by the backend's agent tools (`backend/src/agent/tools/`). Records one
  outreach action.
- `GET /api/v1/dashboard/users/{case_id}` - the case + its full communication
  history, polled by `frontend-demo`.
- `POST /api/v1/dashboard/users/{case_id}/messages` - simulates the customer
  replying on a channel.
- `POST /api/v1/dashboard/users/{case_id}/pay` - simulates the customer
  completing the payment.

State is in-memory only and resets on restart - there is no database here by
design; this service exists purely to feed the demo dashboard.
