import httpx
from src.config.settings import settings

# Configure a shared asynchronous HTTP client for Supabase API interactions.
client = httpx.AsyncClient(
    base_url=settings.supabase_url,
    headers={
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
        "Content-Type": "application/json",
    },
)

async def post(endpoint: str, json: dict | list[dict]) -> dict:
    """POST ``json`` to ``endpoint`` using the shared async client.

    Raises an HTTP error for non‑2xx responses and returns the parsed JSON body.
    """
    resp = await client.post(endpoint, json=json)
    resp.raise_for_status()
    return resp.json()

async def get(endpoint: str, params: dict | None = None) -> dict:
    """GET ``endpoint`` with optional query params using the shared async client.

    Raises for non‑2xx responses and returns the parsed JSON.
    """
    resp = await client.get(endpoint, params=params)
    resp.raise_for_status()
    return resp.json()
