from __future__ import annotations

import re
from collections import defaultdict

from dress_agent.models import Product


SCENE_CATEGORIES = (
    "Prom",
    "Evening",
    "Cocktail",
    "Wedding Guest",
    "Bridesmaid",
    "Homecoming",
    "Party",
)

# Strong scene phrases override design-feature inference.
_SCENE_PHRASES = {
    "Prom": ("prom dress", "prom gown", "prom-dress"),
    "Evening": ("evening dress", "evening gown", "black tie", "gala dress"),
    "Cocktail": ("cocktail dress", "short formal", "semi formal", "semi-formal"),
    "Wedding Guest": ("wedding guest", "wedding-guest", "garden wedding"),
    "Bridesmaid": ("bridesmaid", "maid of honor", "bridal party"),
    "Homecoming": ("homecoming", "hoco dress"),
    "Party": ("party dress", "club dress", "night out", "birthday dress"),
}

# Features are derived from the category distinctions supplied by the product team.
_FEATURES = {
    "Prom": {
        "sparkly": 4, "glitter": 4, "crystal": 3, "beaded": 2,
        "embellished": 2, "ball gown": 5, "princess": 4, "dramatic": 4,
        "layered tulle": 4, "tulle": 2, "train": 2, "mermaid": 2,
        "high slit": 2, "deep v": 2,
    },
    "Evening": {
        "elegant": 4, "luxury": 4, "formal gown": 4, "column": 4,
        "sheath": 4, "velvet": 4, "crepe": 3, "silk": 3, "satin": 2,
        "floor length": 2, "floor-length": 2, "black": 1, "navy": 1,
        "emerald": 1, "burgundy": 1,
    },
    "Cocktail": {
        "cocktail": 8, "knee length": 5, "knee-length": 5,
        "above knee": 4, "fit and flare": 4, "fit & flare": 4,
        "chic": 3, "midi": 2, "bodycon": 2, "off shoulder": 1,
    },
    "Wedding Guest": {
        "floral": 3, "romantic": 3, "wrap": 4, "lace": 2,
        "chiffon": 2, "flowing": 2, "breathable": 2, "midi": 2,
        "maxi": 1, "dusty blue": 2, "champagne": 2, "sage": 2,
        "blush": 2,
    },
    "Bridesmaid": {
        "convertible": 7, "empire": 4, "chiffon": 2, "a-line": 1,
        "sage green": 2, "dusty rose": 2, "champagne": 1, "mauve": 2,
        "wedding party": 7,
    },
    "Homecoming": {
        "short": 4, "mini": 4, "cute": 4, "sparkle": 3,
        "sequin": 3, "skater": 3, "a-line": 1, "bodycon": 1,
    },
    "Party": {
        "sexy": 5, "club": 7, "night out": 7, "birthday": 7,
        "cut out": 3, "cutout": 3, "backless": 2, "mini": 2,
        "bodycon": 3, "slip dress": 3, "metallic": 3, "sheer": 3,
        "corset": 2,
    },
}


def classify_product(product: Product, default: str = "Prom") -> str:
    """Classify a product into one scene using scene and design features."""
    text = _normalized_text(product)

    for category in SCENE_CATEGORIES:
        if any(phrase in text for phrase in _SCENE_PHRASES[category]):
            product.source_category = category
            return category

    scores: dict[str, int] = defaultdict(int)
    # Current monitored collections are Prom collections, so Prom wins weak/tied evidence.
    scores[default] = 1
    for category, features in _FEATURES.items():
        for phrase, weight in features.items():
            if phrase in text:
                scores[category] += weight

    category = max(SCENE_CATEGORIES, key=lambda item: scores[item])
    product.source_category = category
    return category


def _normalized_text(product: Product) -> str:
    raw = " ".join([product.product_title, product.product_url, *product.style_tags])
    normalized = re.sub(r"[-_/]+", " ", raw.lower())
    return f" {re.sub(r'\s+', ' ', normalized).strip()} "
