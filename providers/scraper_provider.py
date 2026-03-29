"""Fallback scraping provider."""

from __future__ import annotations

from typing import Any, Optional


class ScraperProvider:
    """
    Fallback scraper provider.

    This currently returns None by design (as requested),
    and can be implemented later with site-specific parsing.
    """

    def get_price(self, product: dict[str, Any]) -> Optional[dict[str, Any]]:
        _ = product
        return None
