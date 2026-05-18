import json

import httpx
import pytest

from src.llm.lmstudio_client import LMStudioClient


def _mock_response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(json_body).encode(),
        request=httpx.Request("POST", "http://localhost:1234/v1/chat/completions"),
    )


@pytest.fixture
def valid_llm_response():
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "An AI-powered code review tool.",
                            "category": "AI",
                            "business_model": "subscription",
                            "target_users": "Software developers and engineering teams.",
                            "localization_angle": "Could be adapted for Romanian tech companies.",
                            "risk_notes": "Low risk, B2B focused.",
                            "novelty": 4,
                            "idea_potential": 5,
                            "confidence": 4,
                        }
                    )
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_enrich_returns_parsed_result(valid_llm_response):
    async def handler(request):
        return _mock_response(200, valid_llm_response)

    transport = httpx.MockTransport(handler)
    client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
    client._timeout = 5.0

    async def mock_post(self, url, **kwargs):
        response = await transport.handle_async_request(request=httpx.Request("POST", url, json=kwargs.get("json")))
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        result = await client.enrich(domain="example.com")

    assert result.summary == "An AI-powered code review tool."
    assert result.category == "AI"
    assert result.business_model == "subscription"
    assert result.novelty == 4
    assert result.idea_potential == 5
    assert result.confidence == 4


@pytest.mark.asyncio
async def test_enrich_returns_failed_on_http_error():
    async def no_sleep(_seconds):
        return None

    async def handler(request):
        return _mock_response(500, {"error": "Internal server error"})

    transport = httpx.MockTransport(handler)

    async def mock_post(self, url, **kwargs):
        response = await transport.handle_async_request(request=httpx.Request("POST", url, json=kwargs.get("json")))
        response.raise_for_status()
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        mp.setattr("src.llm.lmstudio_client.asyncio.sleep", no_sleep)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        client._timeout = 5.0
        result = await client.enrich(domain="example.com")

    assert "HTTP error" in result.risk_notes
    assert result.novelty == 1


@pytest.mark.asyncio
async def test_post_does_not_retry_non_transient_http_error():
    calls = 0

    async def mock_post(self, url, **kwargs):
        nonlocal calls
        calls += 1
        response = _mock_response(400, {"error": "bad request"})
        response.raise_for_status()
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        with pytest.raises(httpx.HTTPStatusError):
            await client._post({"model": "test-model", "messages": []})

    assert calls == 1


@pytest.mark.asyncio
async def test_post_retries_rate_limit_then_succeeds():
    calls = 0

    async def mock_post(self, url, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                status_code=429,
                headers={"retry-after": "0"},
                content=b'{"error":"rate limited"}',
                request=httpx.Request("POST", url),
            )
        return _mock_response(200, {"choices": [{"message": {"content": "{}"}}]})

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        response = await client._post({"model": "test-model", "messages": []})

    assert response.status_code == 200
    assert calls == 2
    assert client.retry_counts["rate_limited"] == 1


@pytest.mark.asyncio
async def test_enrich_returns_failed_on_invalid_json():
    async def handler(request):
        return _mock_response(200, {"choices": [{"message": {"content": "not valid json"}}]})

    transport = httpx.MockTransport(handler)

    async def mock_post(self, url, **kwargs):
        response = await transport.handle_async_request(request=httpx.Request("POST", url, json=kwargs.get("json")))
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        client._timeout = 5.0
        result = await client.enrich(domain="example.com")

    assert "Invalid JSON" in result.risk_notes


@pytest.mark.asyncio
async def test_enrich_returns_failed_on_validation_error():
    async def handler(request):
        return _mock_response(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Test",
                                    "category": "AI",
                                    "business_model": "subscription",
                                    "target_users": "Devs",
                                    "localization_angle": "Romania",
                                    "risk_notes": "",
                                    "novelty": 10,
                                    "idea_potential": 5,
                                    "confidence": 4,
                                }
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    async def mock_post(self, url, **kwargs):
        response = await transport.handle_async_request(request=httpx.Request("POST", url, json=kwargs.get("json")))
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        client._timeout = 5.0
        result = await client.enrich(domain="example.com")

    assert "Validation error" in result.risk_notes


@pytest.mark.asyncio
async def test_enrich_strips_markdown_code_blocks():
    json_content = json.dumps(
        {
            "summary": "A test site.",
            "category": "Other",
            "business_model": "unknown",
            "target_users": "Everyone",
            "localization_angle": "N/A",
            "risk_notes": "",
            "novelty": 2,
            "idea_potential": 2,
            "confidence": 3,
        }
    )
    wrapped = f"```json\n{json_content}\n```"

    async def handler(request):
        return _mock_response(200, {"choices": [{"message": {"content": wrapped}}]})

    transport = httpx.MockTransport(handler)

    async def mock_post(self, url, **kwargs):
        response = await transport.handle_async_request(request=httpx.Request("POST", url, json=kwargs.get("json")))
        return response

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(httpx.AsyncClient, "post", mock_post)
        client = LMStudioClient(base_url="http://localhost:1234/v1", model="test-model")
        client._timeout = 5.0
        result = await client.enrich(domain="example.com")

    assert result.summary == "A test site."
