from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dress_agent.config import load_config
from dress_agent.classification import classify_product
from dress_agent.models import Product
from dress_agent.reporting import generate_reports
from dress_agent.scoring import score_products
from dress_agent.scrapers import (
    AmericanThreadsScraper,
    AzazieScraper,
    BabybooScraper,
    CoutureCandyScraper,
    EverPrettyScraper,
    JJsHouseScraper,
    LulusScraper,
    MacDuggalScraper,
    MeshkiScraper,
    NewYorkDressScraper,
    OhPollyScraper,
    PrincessPollyScraper,
    PromGirlScraper,
    RevolveScraper,
    SherriHillScraper,
    SimplyDressesScraper,
    StaceesScraper,
    TheDressOutletScraper,
    WindsorScraper,
)
from dress_agent.storage import ProductRepository


LOGGER = logging.getLogger(__name__)
SCRAPERS = {
    "americanthreads": AmericanThreadsScraper,
    "ohpolly": OhPollyScraper,
    "meshki": MeshkiScraper,
    "princesspolly": PrincessPollyScraper,
    "revolve": RevolveScraper,
    "lulus": LulusScraper,
    "windsor": WindsorScraper,
    "everpretty": EverPrettyScraper,
    "stacees": StaceesScraper,
    "jjshouse": JJsHouseScraper,
    "promgirl": PromGirlScraper,
    "azazie": AzazieScraper,
    "newyorkdress": NewYorkDressScraper,
    "sherrihill": SherriHillScraper,
    "macduggal": MacDuggalScraper,
    "couturecandy": CoutureCandyScraper,
    "babyboo": BabybooScraper,
    "thedressoutlet": TheDressOutletScraper,
    "simplydresses": SimplyDressesScraper,
}


def run(
    config_path: str | Path = "config.yaml",
    site_names: set[str] | None = None,
) -> tuple[Path, Path]:
    config = load_config(config_path)
    products: list[Product] = []
    for site_name, scraper_class in SCRAPERS.items():
        if site_names is not None and site_name not in site_names:
            continue
        site_config = config["sites"].get(site_name, {})
        if not site_config.get("enabled", False):
            continue
        try:
            scraper = scraper_class(site_config, config["scraping"])
            site_products = scraper.scrape()
            for product in site_products:
                classify_product(product)
            products.extend(site_products)
            LOGGER.info("Scraped %d products from %s", len(site_products), site_name)
        except Exception:
            LOGGER.exception("Scraping failed for %s; continuing", site_name)

    ranked = score_products(products, config["scoring"]["weights"])
    with ProductRepository(config["database"]["path"]) as repository:
        repository.save_all(ranked)
    report_config = config["reports"]
    return generate_reports(
        ranked, report_config["directory"], int(report_config.get("top_n", 30))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily dress selection agent")
    parser.add_argument("--config", default="config.yaml", help="YAML config path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    markdown_path, json_path = run(args.config)
    LOGGER.info("Generated %s and %s", markdown_path, json_path)
    return 0
