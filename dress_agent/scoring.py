from __future__ import annotations

from dress_agent.models import Product


def score_products(products: list[Product], weights: dict[str, float]) -> list[Product]:
    rank_values = [product.rank_position for product in products]
    review_values = [product.review_count for product in products]
    save_values = [product.like_or_save_count for product in products]

    for product in products:
        rank_score = _normalize(product.rank_position, rank_values, inverse=True)
        review_score = _normalize(product.review_count, review_values)
        save_score = _normalize(product.like_or_save_count, save_values)
        product.score = round(
            weights.get("rank_position", 0) * rank_score
            + weights.get("review_count", 0) * review_score
            + weights.get("like_or_save_count", 0) * save_score,
            4,
        )
        product.score_reason = _reason(product, rank_score, review_score, save_score)
    return sorted(products, key=lambda product: product.score or 0, reverse=True)


def _normalize(
    value: int | float | None,
    values: list[int | float | None],
    inverse: bool = False,
) -> float:
    valid = [float(item) for item in values if item is not None]
    if value is None or not valid:
        return 0.0
    minimum, maximum = min(valid), max(valid)
    if minimum == maximum:
        return 1.0
    normalized = (float(value) - minimum) / (maximum - minimum)
    return 1.0 - normalized if inverse else normalized


def _reason(
    product: Product, rank_score: float, review_score: float, save_score: float
) -> str:
    signals: list[str] = []
    if product.rank_position is not None:
        signals.append(f"榜单第 {product.rank_position} 位")
    if product.review_count is not None:
        signals.append(f"{product.review_count} 条评论")
    if product.like_or_save_count is not None:
        signals.append(f"{product.like_or_save_count} 次点赞/收藏")
    if not signals:
        return "基于当前可用榜单信号入选。"
    strongest = max(
        ((rank_score, "排名"), (review_score, "评论"), (save_score, "收藏"))
    )[1]
    return f"{strongest}信号突出；" + "、".join(signals) + "。"

