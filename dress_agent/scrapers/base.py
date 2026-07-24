from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from dress_agent.models import Product


LOGGER = logging.getLogger(__name__)


class ScrapingDisallowedError(RuntimeError):
    pass


class BaseScraper(ABC):
    source_category = "A"

    def __init__(self, site_config: dict, scraping_config: dict) -> None:
        self.site_config = site_config
        self.base_url = site_config["base_url"].rstrip("/")
        self.collection_urls = site_config.get("collection_urls", [])
        self.user_agent = scraping_config["user_agent"]
        self.timeout = scraping_config.get("timeout_seconds", 20)
        delay = scraping_config.get("delay_seconds", {})
        self.min_delay = float(delay.get("min", 1))
        self.max_delay = float(delay.get("max", 3))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self._robots: RobotFileParser | None = None

    def _robot_parser(self) -> RobotFileParser:
        if self._robots is None:
            robots_url = urljoin(self.base_url, "/robots.txt")
            response = self.session.get(robots_url, timeout=self.timeout)
            response.raise_for_status()
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            self._robots = parser
        return self._robots

    def _ensure_allowed(self, url: str) -> None:
        if urlparse(url).netloc != urlparse(self.base_url).netloc:
            raise ValueError(f"Refusing to scrape a different host: {url}")
        if not self._robot_parser().can_fetch(self.user_agent, url):
            raise ScrapingDisallowedError(f"robots.txt disallows {url}")

    def get(self, url: str) -> requests.Response:
        self._ensure_allowed(url)
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response

    @abstractmethod
    def scrape(self) -> list[Product]:
        raise NotImplementedError

