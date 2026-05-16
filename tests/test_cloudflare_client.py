import json

import httpx
import pytest

from src.cloudflare.client import CloudflareAPIError, CloudflareClient


def _mock_response(status_code: int, json_body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        content=json.dumps(json_body).encode(),
        request=httpx.Request("GET", "https://api.cloudflare.com/client/v4/test"),
    )


@pytest.fixture
def mock_client():
    return CloudflareClient(api_token="test-token")


@pytest.mark.asyncio
async def test_client_sets_auth_header():
    captured_request = None

    async def capture(request):
        nonlocal captured_request
        captured_request = request
        return _mock_response(200, {"success": True, "result": {}})

    transport = httpx.MockTransport(capture)
    client = CloudflareClient(api_token="test-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={
            "Authorization": f"Bearer {client._token}",
            "Content-Type": "application/json",
        },
    )

    await client.get("/test")
    assert captured_request is not None
    assert captured_request.headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_client_raises_on_4xx():
    async def handler(request):
        return _mock_response(401, {"success": False, "errors": [{"message": "Invalid token"}]})

    transport = httpx.MockTransport(handler)
    client = CloudflareClient(api_token="bad-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={"Authorization": "Bearer bad-token", "Content-Type": "application/json"},
    )

    with pytest.raises(CloudflareAPIError) as exc_info:
        await client.get("/test")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_client_raises_on_429():
    async def handler(request):
        return _mock_response(429, {"success": False}, headers={"retry-after": "3"})

    transport = httpx.MockTransport(handler)
    client = CloudflareClient(api_token="test-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.get("/test")
    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
async def test_client_close():
    client = CloudflareClient(api_token="test-token")
    await client.close()
