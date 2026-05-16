from pydantic import BaseModel, Field, field_validator


class GeoParent(BaseModel):
    geo_id: str = Field(alias="geoId")
    name: str
    type: str
    code: str | None = None
    locale: str | None = None


class Geolocation(BaseModel):
    geo_id: str = Field(alias="geoId")
    name: str
    type: str
    code: str | None = None
    locale: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    parent: GeoParent | None = None


class GeolocationsResult(BaseModel):
    geolocations: list[Geolocation]


class GeolocationsResponse(BaseModel):
    success: bool
    result: GeolocationsResult


class Category(BaseModel):
    id: int
    name: str
    super_category_id: int = Field(alias="superCategoryId")


class RankingEntry(BaseModel):
    domain: str
    rank: int
    pct_rank_change: float | None = Field(None, alias="pctRankChange")
    categories: list[Category] = Field(default_factory=list)


class MetaConfidenceInfo(BaseModel):
    level: float | None = None


class MetaDateRange(BaseModel):
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")


class MetaUnit(BaseModel):
    name: str
    value: str


class RankingMeta(BaseModel):
    confidence_info: MetaConfidenceInfo | None = Field(None, alias="confidenceInfo")
    date_range: list[MetaDateRange] = Field(default_factory=list, alias="dateRange")
    last_updated: str | None = Field(None, alias="lastUpdated")
    normalization: str | None = None
    units: list[MetaUnit] = Field(default_factory=list)

    @field_validator("date_range", "units", mode="before")
    @classmethod
    def ensure_list(cls, v):
        return v if v is not None else []


class RankingResult(BaseModel):
    meta: RankingMeta
    top_0: list[RankingEntry]


class RankingResponse(BaseModel):
    success: bool
    result: RankingResult
