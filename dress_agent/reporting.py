from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from dress_agent.models import Product


def generate_reports(
    products: list[Product], output_directory: str | Path, top_n: int = 30
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    report_date = date.today().isoformat()
    markdown_path = directory / f"{report_date}.md"
    json_path = directory / f"{report_date}.json"
    selected = products[:top_n]

    lines = [
        f"# 每日礼服选品报告（{report_date}）",
        "",
        f"共抓取 {len(products)} 款，按第一阶段评分选出 Top {len(selected)}。",
        "",
    ]
    for position, product in enumerate(selected, 1):
        lines.extend(_markdown_product(position, product))
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps([product.to_dict() for product in products], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return markdown_path, json_path


def _markdown_product(position: int, product: Product) -> list[str]:
    price = "暂无"
    if product.price is not None:
        price = f"{product.currency or ''} {product.price:.2f}".strip()
    image = product.product_image_urls[0] if product.product_image_urls else None
    lines = [
        f"## {position}. [{product.product_title}]({product.product_url})",
        "",
    ]
    if image:
        lines.extend([f"![{product.product_title}]({image})", ""])
    lines.extend(
        [
            f"- 来源：{product.source_site}",
            f"- 价格：{price}",
            f"- 榜单排名：{product.rank_position or '暂无'}",
            f"- 评论：{product.review_count if product.review_count is not None else '暂无'}"
            f"（评分 {product.review_rating if product.review_rating is not None else '暂无'}）",
            f"- 点赞/收藏：{product.like_or_save_count if product.like_or_save_count is not None else '暂无'}",
            f"- 选品分：{product.score if product.score is not None else 0:.4f}",
            f"- 入选理由：{product.score_reason or '基于当前可用信号入选。'}",
            "",
        ]
    )
    return lines

