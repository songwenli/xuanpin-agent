from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from dress_agent.models import Product
from dress_agent.scrapers.base import BaseScraper


class ShopifyCollectionScraper(BaseScraper):
    site_name = ""
    default_currency = "USD"
    default_product_url_patterns = ("/products/", "/product/")

    def scrape(self) -> list[Product]:
        products: list[Product] = []
        seen_urls: set[str] = set()
        max_products = int(self.site_config.get("max_products", 60))
        for json_url in self.site_config.get("json_collection_urls", []):
            response = self.get(json_url)
            for product in self._parse_shopify_products(response.json()):
                if product.product_url not in seen_urls:
                    product.rank_position = len(products) + 1
                    products.append(product)
                    seen_urls.add(product.product_url)
                    if len(products) >= max_products:
                        return products
        for collection_url in self.collection_urls:
            response = self.get(collection_url)
            parsed = self.parse_collection(response.text, collection_url)
            for product in parsed:
                if product.product_url not in seen_urls:
                    product.rank_position = len(products) + 1
                    products.append(product)
                    seen_urls.add(product.product_url)
                    if len(products) >= max_products:
                        return products
        return products

    def parse_collection(self, html: str, collection_url: str) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        candidates = (
            self._parse_json_ld(soup)
            + self._parse_embedded_json(soup)
            + self._parse_product_cards(soup, collection_url)
        )
        products: list[Product] = []
        seen: set[str] = set()
        for product in candidates:
            if product.product_url not in seen:
                products.append(product)
                seen.add(product.product_url)
        return products

    def _parse_shopify_products(self, payload: dict) -> list[Product]:
        products: list[Product] = []
        for value in payload.get("products", []):
            variants = value.get("variants") or []
            variant = variants[0] if variants else {}
            images = [image.get("src") for image in value.get("images", []) if image.get("src")]
            tags = value.get("tags") or []
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            product = Product(
                source_site=self.site_name,
                source_category=self.source_category,
                product_url=urljoin(self.base_url, f"/products/{value.get('handle', '')}"),
                product_title=str(value.get("title", "")).strip(),
                product_image_urls=images,
                price=self._float(variant.get("price")),
                currency=self.default_currency,
                is_bestseller_tag=any("best" in tag.lower() for tag in tags),
                is_new_arrival=any("new" in tag.lower() for tag in tags),
                style_tags=tags,
            )
            if product.product_title and value.get("handle"):
                products.append(product)
        return products

    def _parse_json_ld(self, soup: BeautifulSoup) -> list[Product]:
        results: list[Product] = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            nodes = self._json_nodes(payload)
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_type = node.get("@type")
                if node_type == "Product":
                    product = self._product_from_json(node)
                    if product:
                        results.append(product)
                elif node_type == "ItemList":
                    for item in node.get("itemListElement", []):
                        value = item.get("item", item) if isinstance(item, dict) else {}
                        product = self._product_from_json(value)
                        if product:
                            results.append(product)
        return results

    @classmethod
    def _json_nodes(cls, payload: object) -> list[dict]:
        if isinstance(payload, list):
            return [node for item in payload for node in cls._json_nodes(item)]
        if not isinstance(payload, dict):
            return []
        nodes = [payload]
        graph = payload.get("@graph")
        if graph:
            nodes.extend(cls._json_nodes(graph))
        return nodes

    def _product_from_json(self, value: dict) -> Product | None:
        title = value.get("name") or value.get("title")
        url = (
            value.get("url")
            or value.get("onlineStoreUrl")
            or value.get("productUrl")
        )
        if not url and value.get("handle"):
            url = f"/products/{value['handle']}"
        if not title or not url:
            return None
        patterns = tuple(
            self.site_config.get(
                "product_url_patterns", self.default_product_url_patterns
            )
        )
        if not any(pattern in str(url) for pattern in patterns):
            return None
        offer = value.get("offers") or {}
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        images = value.get("image") or value.get("images") or []
        if isinstance(images, str):
            images = [images]
        normalized_images = []
        for image in images:
            if isinstance(image, dict):
                image = image.get("url") or image.get("src")
            if image:
                normalized_images.append(urljoin(self.base_url, image))
        rating = value.get("aggregateRating") or {}
        price = offer.get("price") or value.get("price") or value.get("priceAmount")
        if isinstance(price, dict):
            price = price.get("amount") or price.get("value")
        return Product(
            source_site=self.site_name,
            source_category=self.source_category,
            product_url=urljoin(self.base_url, url),
            product_title=title.strip(),
            product_image_urls=normalized_images,
            price=self._float(price),
            currency=offer.get("priceCurrency") or value.get("currency") or self.default_currency,
            review_count=self._int(rating.get("reviewCount")),
            review_rating=self._float(rating.get("ratingValue")),
            is_bestseller_tag=True,
        )

    def _parse_embedded_json(self, soup: BeautifulSoup) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()
        for script in soup.select('script[type="application/json"], script#__NEXT_DATA__'):
            try:
                payload = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            for value in self._walk_dicts(payload):
                product = self._product_from_json(value)
                if product and product.product_url not in seen:
                    products.append(product)
                    seen.add(product.product_url)
        return products

    @classmethod
    def _walk_dicts(cls, value: object):
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from cls._walk_dicts(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from cls._walk_dicts(nested)

    def _parse_product_cards(
        self, soup: BeautifulSoup, collection_url: str
    ) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()
        patterns = tuple(
            self.site_config.get(
                "product_url_patterns", self.default_product_url_patterns
            )
        )
        for link in soup.select("a[href]"):
            href = link.get("href")
            if not href or not any(pattern in href for pattern in patterns):
                continue
            url = urljoin(collection_url, href.split("?")[0])
            if url in seen:
                continue
            card = link.find_parent(["article", "li"]) or link.find_parent("div") or link
            title_node = card.select_one(
                "[data-product-title], [class*='product'][class*='title'], "
                ".card__heading, .product-card__title, .product-title, h2, h3"
            )
            title = (
                (title_node or link).get("title")
                or (title_node or link).get("aria-label")
                or (title_node or link).get_text(" ", strip=True)
            )
            if not title:
                continue
            image_nodes = card.select("img")
            images = []
            for image in image_nodes:
                source = image.get("src") or image.get("data-src")
                if source:
                    images.append(urljoin(collection_url, source))
            text = card.get_text(" ", strip=True)
            price_node = card.select_one(
                "[data-price], [class*='price'], .price, .product-price"
            )
            review_count, review_rating = self._reviews(card)
            products.append(
                Product(
                    source_site=self.site_name,
                    source_category=self.source_category,
                    product_url=url,
                    product_title=title,
                    product_image_urls=list(dict.fromkeys(images)),
                    price=self._price(price_node.get_text(" ", strip=True))
                    if price_node
                    else None,
                    currency=self.default_currency,
                    review_count=review_count,
                    review_rating=review_rating,
                    is_bestseller_tag="best seller" in text.lower()
                    or "bestseller" in text.lower(),
                    is_new_arrival="new arrival" in text.lower()
                    or "new" in text.lower().split(),
                )
            )
            seen.add(url)
        return products

    @classmethod
    def _reviews(cls, card) -> tuple[int | None, float | None]:
        rating_node = card.select_one(
            "[data-rating], [data-review-count], [class*='rating'], [class*='review']"
        )
        if not rating_node:
            return None, None
        text = rating_node.get_text(" ", strip=True)
        count_value = rating_node.get("data-review-count")
        rating_value = rating_node.get("data-rating")
        count_match = re.search(r"(?:\(|\b)(\d[\d,]*)\s*(?:reviews?|\))", text, re.I)
        rating_match = re.search(r"([0-5](?:\.\d+)?)\s*(?:/\s*5|stars?)", text, re.I)
        return (
            cls._int(str(count_value).replace(",", ""))
            if count_value is not None
            else cls._int(count_match.group(1).replace(",", ""))
            if count_match
            else None,
            cls._float(rating_value)
            if rating_value is not None
            else cls._float(rating_match.group(1))
            if rating_match
            else None,
        )

    @staticmethod
    def _float(value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: object) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _price(cls, value: str) -> float | None:
        match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", value)
        return float(match.group(0).replace(",", "")) if match else None
