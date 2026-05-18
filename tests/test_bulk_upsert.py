import pytest
from unittest.mock import AsyncMock

# Import the functions to test
from src.db import repositories

@pytest.mark.asyncio
async def test_bulk_upsert_domains_batch_calls(monkeypatch):
    # Prepare a list larger than one batch (e.g., 1800 items => 3 batches of 800)
    total = 1800
    domains = [{"normalized_domain": f"domain{i}.com"} for i in range(total)]

    calls = []
    async def mock_post(endpoint: str, json):
        calls.append((endpoint, json))
        return {"status": "ok"}

    monkeypatch.setattr(repositories, "post", mock_post)

    await repositories.bulk_upsert_domains(domains)

    # Expect three calls with batch size 800
    assert len(calls) == 3
    for idx, (endpoint, batch) in enumerate(calls):
        assert endpoint == "/rest/v1/domains"
        assert isinstance(batch, list)
        # All full batches should be 800, last batch may be smaller
        if idx < len(calls) - 1:
            assert len(batch) == 800
        else:
            assert len(batch) == total % 800 or len(batch) == 800


    # Verify that all items were sent
    sent_items = [item for _, batch in calls for item in batch]
    assert len(sent_items) == total
    assert sent_items == domains

@pytest.mark.asyncio
async def test_bulk_insert_observations_batch_calls(monkeypatch):
    total = 1600
    observations = [{"domain_id": f"id{i}"} for i in range(total)]
    calls = []
    async def mock_post(endpoint: str, json):
        calls.append((endpoint, json))
        return {"status": "ok"}

    monkeypatch.setattr(repositories, "post", mock_post)

    await repositories.bulk_insert_observations(observations)

    # Expect two calls of 800 each
    assert len(calls) == 2
    for endpoint, batch in calls:
        assert endpoint == "/rest/v1/observations"
        assert isinstance(batch, list)
        assert len(batch) == 800

    sent_items = [item for _, batch in calls for item in batch]
    assert len(sent_items) == total
    assert sent_items == observations
