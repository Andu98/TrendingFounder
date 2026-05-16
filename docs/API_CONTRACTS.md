# API Contracts

## Cloudflare Radar API

### GET /radar/ranking/top

Returns top or trending domains for a given location.

**Query Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `location` | Yes | Country alpha-2 code (e.g., `US`, `RO`) |
| `rankingType` | Yes | `POPULAR`, `TRENDING_RISE`, or `TRENDING_STEADY` |
| `limit` | No | Number of results (default varies, recommend 50-100) |
| `format` | No | `JSON` |
| `date` | No | Specific date (YYYY-MM-DD) |
| `domainCategory` | No | Filter by category |
| `name` | No | Filter by domain name |

**Authentication:** Bearer token via `Authorization: Bearer <CLOUDFLARE_API_TOKEN>`

**Response Shape:**

```json
{
  "result": {
    "meta": {
      "locationInfo": {...},
      "rankingType": "TRENDING_RISE",
      "date": "2026-05-15"
    },
    "top_0": [
      {
        "domain": "example.com",
        "rank": 1,
        "pctRankChange": 150.5,
        "categories": ["AI", "SaaS"]
      }
    ]
  }
}
```

**Notes:**
- `pctRankChange` is only present for `TRENDING_RISE` and `TRENDING_STEADY` ranking types.
- `top_0` naming is literal — the field is always `top_0` regardless of limit.

### GET /radar/geolocations

Returns list of geolocations (continents, countries, admin regions).

**Query Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `format` | No | `JSON` |
| `geoId` | No | Filter by geolocation ID |
| `limit` | No | Max results |
| `location` | No | Filter by location name |
| `offset` | No | Pagination offset |

**Response Shape:**

```json
{
  "result": {
    "locations": [
      {
        "geolocation_id": "US",
        "geolocation_name": "United States",
        "type": "COUNTRY"
      }
    ]
  }
}
```

**Notes:**
- Filter results to `type == "COUNTRY"` only for this project.

### Rate Limits

- Global: 1200 requests / 5 minutes per user/account token
- Per IP: 200 requests / second
- HTTP 429 returned when exceeded; respect `Ratelimit` and `retry-after` headers.
