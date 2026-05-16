from src.cloudflare.client import CloudflareClient
from src.cloudflare.schemas import (
    GeolocationsResponse,
    RankingEntry,
    RankingResponse,
)
from src.config.constants import COUNTRY_CODES, RankingType
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RadarService:
    def __init__(self, client: CloudflareClient | None = None):
        self._client = client or CloudflareClient()

    async def get_geolocations(
        self,
        limit: int = 300,
        location_type: str = "COUNTRY",
    ) -> list[dict]:
        params = {"format": "JSON", "limit": limit}
        response = await self._client.get("/radar/geolocations", params=params)
        data = response.json()

        parsed = GeolocationsResponse.model_validate(data)

        countries = [
            {
                "code": loc.code,
                "name": loc.name,
                "geo_id": loc.geo_id,
            }
            for loc in parsed.result.geolocations
            if loc.type == location_type and loc.code is not None
        ]

        if len(countries) < 50:
            logger.warning(
                f"Cloudflare returned only {len(countries)} countries. "
                f"Falling back to hardcoded list of {len(COUNTRY_CODES)} countries."
            )
            countries = [{"code": code, "name": name, "geo_id": ""} for code, name in COUNTRY_CODES.items()]

        logger.info(f"Using {len(countries)} countries for crawl.")
        return countries

    async def get_top_domains(
        self,
        location: str,
        ranking_type: RankingType,
        limit: int = 100,
    ) -> list[RankingEntry]:
        params = {
            "format": "JSON",
            "location": location,
            "rankingType": ranking_type.value,
            "limit": limit,
        }

        response = await self._client.get("/radar/ranking/top", params=params)
        data = response.json()

        parsed = RankingResponse.model_validate(data)

        if not parsed.success:
            logger.error(
                f"Cloudflare ranking API returned success=false for {location}/{ranking_type.value}. "
                f"Raw payload: {data}"
            )
            return []

        entries = parsed.result.top_0
        logger.info(f"Fetched {len(entries)} domains for {location}/{ranking_type.value}.")
        return entries
