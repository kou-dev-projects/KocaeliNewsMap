from typing import Optional

from pydantic import BaseModel, ConfigDict


class HaberBase(BaseModel):
    title: str
    summary: Optional[str] = None
    source_name: str
    source_domain: str
    source_base_url: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    published_at_raw: Optional[str] = None


class HaberCreate(HaberBase):
    content_text: str


class HaberListItem(HaberBase):
    id: str
    scraped_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HaberResponse(HaberListItem):
    content_text: str


class HaberListResponse(BaseModel):
    items: list[HaberListItem]
    total: int
