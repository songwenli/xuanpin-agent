import tempfile
import unittest
from pathlib import Path

from dress_agent.reporting import generate_reports
from dress_agent.models import Product
from dress_agent.scoring import score_products
from dress_agent.scrapers.lulus import LulusScraper
from dress_agent.storage import ProductRepository
from dress_agent.cli import SCRAPERS
from dress_agent.config import load_config
from dress_agent.classification import classify_product


SAMPLE_HTML = """
<script type="application/ld+json">
{
  "@type": "ItemList",
  "itemListElement": [{
    "item": {
      "name": "Test Dress",
      "url": "/products/test-dress",
      "image": "/images/test.jpg",
      "offers": {"price": "99.00", "priceCurrency": "USD"},
      "aggregateRating": {"reviewCount": "12", "ratingValue": "4.8"}
    }
  }]
}
</script>
"""


class PipelineTest(unittest.TestCase):
    def test_scene_classification(self) -> None:
        cases = {
            "Satin Bridesmaid Maxi Dress": "Bridesmaid",
            "Short Homecoming Dress": "Homecoming",
            "Wedding Guest Floral Midi": "Wedding Guest",
            "Sequin Cocktail Mini Dress": "Cocktail",
            "Black Tie Evening Gown": "Evening",
            "Birthday Party Mini Dress": "Party",
            "Crystal Beaded Tulle Ball Gown": "Prom",
            "Black Velvet Column Gown": "Evening",
            "Floral Chiffon Wrap Midi Dress": "Wedding Guest",
            "Cute Short Sequin A-Line Dress": "Homecoming",
            "Sexy Metallic Cutout Bodycon Mini": "Party",
            "Classic Strapless Gown": "Prom",
        }
        for title, expected in cases.items():
            product = Product("example", "", "https://example.com/item", title)
            self.assertEqual(classify_product(product), expected)

    def test_all_configured_sites_have_scrapers(self) -> None:
        config = load_config()
        self.assertEqual(len(SCRAPERS), 19)
        self.assertEqual(set(SCRAPERS), set(config["sites"]))

    def test_parse_score_store_and_report(self) -> None:
        scraper = LulusScraper(
            {"base_url": "https://www.lulus.com", "collection_urls": []},
            {"user_agent": "test-agent", "delay_seconds": {"min": 0, "max": 0}},
        )
        products = scraper.parse_collection(SAMPLE_HTML, "https://www.lulus.com/test")
        self.assertEqual(len(products), 1)
        products[0].rank_position = 1

        ranked = score_products(
            products,
            {"rank_position": 0.25, "review_count": 0.15, "like_or_save_count": 0.25},
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with ProductRepository(root / "products.db") as repository:
                self.assertEqual(repository.save_all(ranked), 1)
                self.assertEqual(repository.count_products(), 1)
                stored = repository.list_products()
                self.assertEqual(stored[0]["product_title"], "Test Dress")
                self.assertEqual(stored[0]["product_image_urls"], ["https://www.lulus.com/images/test.jpg"])
            markdown_path, json_path = generate_reports(ranked, root / "reports")
            self.assertTrue(json_path.exists())
            self.assertIn("Test Dress", markdown_path.read_text(encoding="utf-8"))

    def test_products_are_listed_newest_first(self) -> None:
        older = Product(
            source_site="example",
            source_category="dresses",
            product_url="https://example.com/older",
            product_title="Older high score",
            scraped_at="2026-07-21T10:00:00+00:00",
            score=1.0,
        )
        newer = Product(
            source_site="example",
            source_category="dresses",
            product_url="https://example.com/newer",
            product_title="Newer low score",
            scraped_at="2026-07-22T10:00:00+00:00",
            score=0.1,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            with ProductRepository(Path(temporary_directory) / "products.db") as repository:
                repository.save_all([older, newer])
                stored = repository.list_products()

        self.assertEqual(
            [product["product_title"] for product in stored],
            ["Newer low score", "Older high score"],
        )

    def test_products_can_be_filtered_by_scene_category(self) -> None:
        products = [
            Product("example", "Prom", "https://example.com/prom", "Prom Dress"),
            Product("example", "Evening", "https://example.com/evening", "Evening Gown"),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            with ProductRepository(Path(temporary_directory) / "products.db") as repository:
                repository.save_all(products)
                evening = repository.list_products(category="Evening")
                self.assertEqual(repository.count_products(category="Evening"), 1)

        self.assertEqual([product["product_title"] for product in evening], ["Evening Gown"])


if __name__ == "__main__":
    unittest.main()
