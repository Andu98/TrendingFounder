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

## GitHub Search API

### GET /search/repositories

Returns repositories matching the `topic:opencode` query, sorted by stars descending.

**Base URL:** `https://api.github.com`

**Query Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `q` | Yes | Search query. This app uses `topic:opencode`. |
| `sort` | No | Sort field. This app uses `stars`. |
| `order` | No | Sort direction. This app uses `desc`. |
| `per_page` | No | Page size. This app uses `100`. |
| `page` | No | Page number. This app fetches pages `1` through `5`. |

**Headers:**

| Header | Required | Description |
|---|---|---|
| `Accept` | Yes | `application/vnd.github+json` |
| `Authorization` | No | `Bearer <GITHUB_TOKEN>` when `GITHUB_TOKEN` is configured |

**Response Shape:**

```json
{
  "total_count": 123,
  "incomplete_results": false,
  "items": [
    {
      "id": 123456,
      "full_name": "owner/repo",
      "owner": {"login": "owner"},
      "name": "repo",
      "html_url": "https://github.com/owner/repo",
      "description": "Repository description",
      "language": "Python",
      "stargazers_count": 1000,
      "forks_count": 100,
      "open_issues_count": 10,
      "pushed_at": "2026-05-18T10:00:00Z",
      "updated_at": "2026-05-18T11:00:00Z",
      "created_at": "2026-05-17T09:00:00Z"
    }
  ]
}
```

**Notes:**
- This feature fetches at most 500 repositories: 5 pages × 100 results.
- First run is baseline-only: rows are stored with `is_baseline = true` and `is_new = false`.
- Later runs compare `github_repo_id` against existing rows and mark only previously unseen repositories as new.
- HTTP 403/429 with exhausted rate limit marks the GitHub crawl run as failed with the error stored in `github_repo_crawl_runs.error`.
