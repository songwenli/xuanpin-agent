from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from dress_agent.models import Product
from dress_agent.classification import classify_product


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_site TEXT NOT NULL,
    source_category TEXT NOT NULL,
    product_url TEXT NOT NULL,
    product_title TEXT NOT NULL,
    product_image_urls TEXT NOT NULL DEFAULT '[]',
    price REAL,
    currency TEXT,
    rank_position INTEGER,
    review_count INTEGER,
    review_rating REAL,
    like_or_save_count INTEGER,
    is_bestseller_tag INTEGER NOT NULL DEFAULT 0,
    is_new_arrival INTEGER NOT NULL DEFAULT 0,
    color TEXT,
    style_tags TEXT NOT NULL DEFAULT '[]',
    scraped_at TEXT NOT NULL,
    score REAL,
    score_reason TEXT,
    UNIQUE(source_site, product_url, scraped_at)
);
CREATE INDEX IF NOT EXISTS idx_products_scraped_at ON products(scraped_at);
CREATE INDEX IF NOT EXISTS idx_products_score ON products(score DESC);
"""


class ProductRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ProductRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def save_all(self, products: Iterable[Product]) -> int:
        rows = [self._to_row(product) for product in products]
        if not rows:
            return 0
        before = self.connection.total_changes
        self.connection.executemany(
            """
            INSERT INTO products (
                source_site, source_category, product_url, product_title,
                product_image_urls, price, currency, rank_position,
                review_count, review_rating, like_or_save_count,
                is_bestseller_tag, is_new_arrival, color, style_tags,
                scraped_at, score, score_reason
            ) VALUES (
                :source_site, :source_category, :product_url, :product_title,
                :product_image_urls, :price, :currency, :rank_position,
                :review_count, :review_rating, :like_or_save_count,
                :is_bestseller_tag, :is_new_arrival, :color, :style_tags,
                :scraped_at, :score, :score_reason
            )
            ON CONFLICT(source_site, product_url, scraped_at) DO UPDATE SET
                product_title=excluded.product_title,
                product_image_urls=excluded.product_image_urls,
                price=excluded.price,
                currency=excluded.currency,
                rank_position=excluded.rank_position,
                review_count=excluded.review_count,
                review_rating=excluded.review_rating,
                like_or_save_count=excluded.like_or_save_count,
                is_bestseller_tag=excluded.is_bestseller_tag,
                is_new_arrival=excluded.is_new_arrival,
                color=excluded.color,
                style_tags=excluded.style_tags,
                score=excluded.score,
                score_reason=excluded.score_reason
            """,
            rows,
        )
        self.connection.commit()
        return self.connection.total_changes - before

    def list_products(
        self, limit: int = 100, offset: int = 0, category: str | None = None
    ) -> list[dict]:
        rows = self.connection.execute(
            """
            SELECT * FROM (
                SELECT products.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY source_site, product_url
                           ORDER BY scraped_at DESC
                       ) AS version_rank
                FROM products
            )
            WHERE version_rank = 1
              AND (? IS NULL OR source_category = ?)
            ORDER BY scraped_at DESC, score DESC, rank_position ASC, id DESC
            LIMIT ? OFFSET ?
            """,
            (category, category, limit, offset),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def count_products(self, category: str | None = None) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS total FROM (
                SELECT source_category,
                       ROW_NUMBER() OVER (
                           PARTITION BY source_site, product_url
                           ORDER BY scraped_at DESC
                       ) AS version_rank
                FROM products
            )
            WHERE version_rank = 1
              AND (? IS NULL OR source_category = ?)
            """,
            (category, category),
        ).fetchone()
        return int(row["total"])

    def classify_all_products(self) -> int:
        rows = self.connection.execute(
            "SELECT id, source_category, product_url, product_title, style_tags FROM products"
        ).fetchall()
        updates = []
        for row in rows:
            product = Product(
                source_site="",
                source_category=row["source_category"],
                product_url=row["product_url"],
                product_title=row["product_title"],
                style_tags=json.loads(row["style_tags"]),
            )
            updates.append((classify_product(product), row["id"]))
        self.connection.executemany(
            "UPDATE products SET source_category = ? WHERE id = ?", updates
        )
        self.connection.commit()
        return len(updates)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> dict:
        product = dict(row)
        product.pop("version_rank", None)
        product["product_image_urls"] = json.loads(product["product_image_urls"])
        product["style_tags"] = json.loads(product["style_tags"])
        product["is_bestseller_tag"] = bool(product["is_bestseller_tag"])
        product["is_new_arrival"] = bool(product["is_new_arrival"])
        return product

    @staticmethod
    def _to_row(product: Product) -> dict:
        row = product.to_dict()
        row["product_image_urls"] = json.dumps(
            row["product_image_urls"], ensure_ascii=False
        )
        row["style_tags"] = json.dumps(row["style_tags"], ensure_ascii=False)
        row["is_bestseller_tag"] = int(row["is_bestseller_tag"])
        row["is_new_arrival"] = int(row["is_new_arrival"])
        return row
