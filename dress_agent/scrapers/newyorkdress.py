from dress_agent.scrapers.shopify import ShopifyCollectionScraper


class NewYorkDressScraper(ShopifyCollectionScraper):
    site_name = "newyorkdress.com"
    source_category = "B"

