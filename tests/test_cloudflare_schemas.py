from src.cloudflare.schemas import (
    GeolocationsResponse,
    RankingResponse,
)


def test_geolocations_response_parsing():
    raw = {
        "success": True,
        "result": {
            "geolocations": [
                {
                    "geoId": "6252001",
                    "name": "United States",
                    "type": "COUNTRY",
                    "code": "US",
                    "latitude": "38",
                    "longitude": "-97",
                    "parent": None,
                    "locale": None,
                },
                {
                    "geoId": "2267056",
                    "name": "Lisbon",
                    "type": "ADM1",
                    "code": "PT-11",
                    "latitude": "10",
                    "longitude": "10",
                    "parent": None,
                    "locale": None,
                },
            ]
        },
    }

    parsed = GeolocationsResponse.model_validate(raw)
    assert parsed.success is True
    assert len(parsed.result.geolocations) == 2
    assert parsed.result.geolocations[0].code == "US"
    assert parsed.result.geolocations[1].type == "ADM1"


def test_ranking_response_parsing():
    raw = {
        "success": True,
        "result": {
            "meta": {
                "confidenceInfo": {"level": 0.95},
                "dateRange": [{"startTime": "2026-05-15T00:00:00Z", "endTime": "2026-05-15T23:59:59Z"}],
                "lastUpdated": "2026-05-16T00:00:00Z",
                "normalization": "PERCENTAGE",
                "units": [{"name": "*", "value": "requests"}],
            },
            "top_0": [
                {
                    "domain": "example.com",
                    "rank": 1,
                    "pctRankChange": 150.5,
                    "categories": [{"id": 81, "name": "Content Servers", "superCategoryId": 26}],
                },
                {
                    "domain": "novel-site.io",
                    "rank": 2,
                    "pctRankChange": None,
                    "categories": [],
                },
            ],
        },
    }

    parsed = RankingResponse.model_validate(raw)
    assert parsed.success is True
    assert len(parsed.result.top_0) == 2
    assert parsed.result.top_0[0].domain == "example.com"
    assert parsed.result.top_0[0].pct_rank_change == 150.5
    assert parsed.result.top_0[1].pct_rank_change is None
    assert parsed.result.top_0[0].categories[0].name == "Content Servers"


def test_ranking_response_empty_top():
    raw = {
        "success": True,
        "result": {
            "meta": {
                "confidenceInfo": None,
                "dateRange": [],
                "lastUpdated": None,
                "normalization": None,
                "units": [],
            },
            "top_0": [],
        },
    }

    parsed = RankingResponse.model_validate(raw)
    assert parsed.success is True
    assert len(parsed.result.top_0) == 0
