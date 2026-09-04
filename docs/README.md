# Razorpay Agent API Documentation Portal

A developer API reference and interactive documentation portal styled after [Razorpay's API Reference](https://razorpay.com/docs/api), covering the complete backend API of the **Razorpay Agent Autonomous Payment Recovery System**.

---

## 🌟 Features

- **Razorpay Design System:** Faithful reproduction of Razorpay / Mintlify 3-column developer portal aesthetic, including signature Razorpay blue (`#0c6cf2`), deep dark mode (`#0b0c10`), crisp badges, and typography.
- **Complete Endpoint Coverage:** Every endpoint across Onboarding, Recovery Cases, Webhook Events, and Ingress is documented with parameter constraints, types, and error codes.
- **Multi-Language Code Generators:** Instant code snippets in **cURL**, **Python (requests)**, **Node.js (fetch)**, and **Go**.
- **Interactive Playground (Try It):** Test requests directly from your browser against your local backend (`http://localhost:8000`) or custom staging servers with latency timing and response inspection.
- **Production Webhook Catalog:** Integrated with 36 real webhook event payloads from `./docs/webhooks` covering Payment Failures (Card, UPI, Netbanking, Wallet), Subscriptions (Paused, Halted, Cancelled), Payment Links, and Provider Downtimes.
- **Instant Search (⌘K):** Keyboard-driven command palette searching endpoints, parameters, and guides.
- **OpenAPI 3.1 & Swagger UI:** Includes `openapi.json` generated from the live FastAPI schemas and a bundled `swagger.html` viewer.

---

## 📂 Directory Structure

```
docs/
├── index.html               # Main Razorpay-style API Reference Portal (Root)
├── build_docs.py            # Automated builder script generating docs from OpenAPI & Webhook schemas
├── README.md                # This guide
├── api/
│   ├── index.html           # Nested route entrypoint (/docs/api)
│   ├── style.css            # Razorpay CSS theme (Dark & Light modes)
│   ├── app.js               # Reactive playground, code generator & search
│   ├── openapi.json         # Complete OpenAPI 3.1.0 schema
│   └── swagger.html         # Standalone Swagger UI viewer
└── webhooks/                # Subscribed Razorpay Webhook Payload Catalog
    ├── downtime_webhooks/   # Card issuer, UPI, netbanking, payout outages
    └── recovery_webhooks/   # Payment, subscription, invoice, dispute failures
```

---

## 🚀 How to View Locally

### Option 1: Direct File Access
You can open `docs/index.html` directly in any web browser (`file:///.../docs/index.html`).

### Option 2: Python Local Server (Recommended for Live Playground)
To test the interactive API playground against your local backend:
```bash
# In the project root:
python3 -m http.server 8080 --directory docs
```
Then visit: **[http://localhost:8080](http://localhost:8080)**

---

## 🔄 Re-generating Docs

If backend endpoints or Pydantic models in `backend/src` change, re-generate the documentation by running:
```bash
# 1. Export fresh openapi.json from the backend
cd backend
DEBUG=false uv run python -c "from src.main import app; import json; open('../docs/api/openapi.json', 'w').write(json.dumps(app.openapi(), indent=2))"

# 2. Re-build the HTML pages
cd ..
python3 docs/build_docs.py
```

