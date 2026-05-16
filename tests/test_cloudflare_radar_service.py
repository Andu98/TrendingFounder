import json

import httpx
import pytest

from src.cloudflare.client import CloudflareClient
from src.cloudflare.radar_service import RadarService
from src.config.constants import RankingType


def _mock_response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(json_body).encode(),
        request=httpx.Request("GET", "https://api.cloudflare.com/client/v4/test"),
    )


@pytest.fixture
def geolocations_raw():
    countries = [{"geoId": str(i), "name": f"Country {i}", "type": "COUNTRY", "code": f"C{i}"} for i in range(60)]
    countries.append({"geoId": "999", "name": "Lisbon", "type": "ADM1", "code": "PT-11"})
    return {"success": True, "result": {"geolocations": countries}}


@pytest.fixture
def ranking_raw():
    return {
        "success": True,
        "result": {
            "meta": {
                "confidenceInfo": {"level": 0.9},
                "dateRange": [],
                "lastUpdated": "2026-05-16T00:00:00Z",
                "normalization": "PERCENTAGE",
                "units": [],
            },
            "top_0": [
                {
                    "domain": "rising-app.com",
                    "rank": 1,
                    "pctRankChange": 200.0,
                    "categories": [{"id": 1, "name": "AI", "superCategoryId": 0}],
                },
                {
                    "domain": "steady-site.org",
                    "rank": 2,
                    "pctRankChange": 10.0,
                    "categories": [],
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_get_geolocations_filters_countries(geolocations_raw):
    async def handler(request):
        return _mock_response(200, geolocations_raw)

    transport = httpx.MockTransport(handler)
    client = CloudflareClient(api_token="test-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    )

    service = RadarService(client=client)
    countries = await service.get_geolocations()

    assert len(countries) == 60
    assert countries[0]["code"] == "C0"
    assert countries[1]["code"] == "C1"


@pytest.mark.asyncio
async def test_get_top_domains_returns_entries(ranking_raw):
    async def handler(request):
        return _mock_response(200, ranking_raw)

    transport = httpx.MockTransport(handler)
    client = CloudflareClient(api_token="test-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    )

    service = RadarService(client=client)
    entries = await service.get_top_domains("US", RankingType.TRENDING_RISE, limit=50)

    assert len(entries) == 2
    assert entries[0].domain == "rising-app.com"
    assert entries[0].rank == 1
    assert entries[0].pct_rank_change == 200.0
    assert entries[1].domain == "steady-site.org"


@pytest.mark.asyncio
async def test_get_top_domains_returns_empty_on_success_false():
    raw = {"success": False, "result": {"meta": {}, "top_0": []}}

    async def handler(request):
        return _mock_response(200, raw)

    transport = httpx.MockTransport(handler)
    client = CloudflareClient(api_token="test-token")
    client._client = httpx.AsyncClient(
        base_url=client.BASE_URL,
        transport=transport,
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    )

    service = RadarService(client=client)
    entries = await service.get_top_domains("US", RankingType.POPULAR)

    assert entries == []
