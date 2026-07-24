from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Product:
    source_site: str
    source_category: str
    product_url: str
    product_title: str
    product_image_urls: list[str] = field(default_factory=list)
    price: float | None = None
    currency: str | None = None
    rank_position: int | None = None
    review_count: int | None = None
    review_rating: float | None = None
    like_or_save_count: int | None = None
    is_bestseller_tag: bool = False
    is_new_arrival: bool = False
    color: str | None = None
    style_tags: list[str] = field(default_factory=list)
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    score: float | None = None
    score_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

