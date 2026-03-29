from typing import Optional

from pydantic import BaseModel, ConfigDict


class NewsBase(BaseModel):
    title: str
    summary: Optional[str] = None
    source_name: str
    source_domain: str
    source_base_url: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    published_at_raw: Optional[str] = None


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
