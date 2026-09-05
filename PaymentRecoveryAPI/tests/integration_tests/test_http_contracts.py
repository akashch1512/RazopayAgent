import httpx
import pytest
from fastapi import FastAPI


@pytest.fixture(name="http_contract_client")
async def http_contract_client(backend_test_app: FastAPI):
    """Exercise the ASGI app without opening external database connections."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=backend_test_app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.anyio
async def test_health_endpoint_returns_service_status(http_contract_client: httpx.AsyncClient) -> None:
    response = await http_contract_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_openapi_describes_public_api(http_contract_client: httpx.AsyncClient) -> None:
    response = await http_contract_client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert document["info"]["title"] == "Razopay Agent API"
    for path in (
        "/api/health",
        "/api/webhooks/razorpay",
        "/api/webhooks/events/{event_id}",
        "/api/businesses/",
        "/api/businesses/{business_id}/webhook",
        "/api/businesses/{business_id}/settings",
        "/api/invoices/{business_id}",
        "/api/invoices/{business_id}/{invoice_id}/chase",
        "/api/recovery-cases/",
        "/api/recovery-cases/{case_id}/feedback",
        "/api/recovery-cases/{case_id}/mark-paid",
        "/api/recovery-cases/businesses/{business_id}/start",
        "/api/integrations/razorpay/callback",
    ):
        assert path in document["paths"], path


@pytest.mark.anyio
async def test_unknown_route_returns_json_404(http_contract_client: httpx.AsyncClient) -> None:
    response = await http_contract_client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.anyio
async def test_recovery_case_limit_validation_is_enforced(
    http_contract_client: httpx.AsyncClient,
) -> None:
    response = await http_contract_client.get("/api/recovery-cases/", params={"limit": 0})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "limit"


@pytest.mark.anyio
async def test_cors_preflight_allows_configured_frontend(
    http_contract_client: httpx.AsyncClient,
) -> None:
    response = await http_contract_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"