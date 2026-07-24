from dress_agent.scrapers.shopify import ShopifyCollectionScraper


class LulusScraper(ShopifyCollectionScraper):
    site_name = "lulus.com"
    default_currency = "USD"

