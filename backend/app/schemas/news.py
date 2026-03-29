from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsBase(BaseModel):
    title: str
    summary: Optional[str] = None
    source_name: str
    source_domain: str
    source_base_url: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    published_at_raw: Optional[str] = None
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    district: Optional[str] = None
    district_confidence: Optional[float] = None
    geocode_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_domains: list[str] = Field(default_factory=list)


class NewsCreate(NewsBase):
    content_text: str


class NewsListItem(NewsBase):
    id: str
    scraped_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NewsResponse(NewsListItem):
    content_text: str


class NewsListResponse(BaseModel):
    items: list[NewsListItem]
    total: int


class NewsMapItem(BaseModel):
    id: str
    title: str
    source_name: str
    source_domain: str
    url: str
    published_at_raw: Optional[str] = None
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    district: Optional[str] = None
    geocode_status: str
    latitude: float
    longitude: float


class NewsMapResponse(BaseModel):
    items: list[NewsMapItem]
    total: int


class StatsBucket(BaseModel):
    key: str
    count: int


class NewsStatsResponse(BaseModel):
    total: int
    geocoded_total: int
    last_24h_total: int
    active_sources: int
    categories: list[StatsBucket]
    districts: list[StatsBucket]
