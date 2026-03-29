"""RapidAPI-backed provider for product prices."""

from __future__ import annotations

import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiProvider:
    """Fetch prices from RapidAPI endpoints configured per product."""

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_price(self, product: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Return standardized result: {"price": float, "source": "api"}.
        Returns None if API is not configured or if API call fails.
        """
        api_config = product.get("api") or {}
        if not api_config.get("enabled"):
            return None

        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return None

        api_url = api_config.get("url")
        api_host = api_config.get("host")
        if not api_url or not api_host:
            return None

        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": api_host,
            "Accept": "application/json",
        }
        params = api_config.get("params") or {}

        try:
            response = self.session.get(
                api_url,
                headers=headers,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None

        price = self._extract_price(payload)
        if price is None:
            return None

        return {"price": price, "source": "api"}

    @staticmethod
    def _extract_price(payload: Any) -> Optional[float]:
        """
        Try common fields from RapidAPI product payloads.
        Supports values such as:
        - data.product_price
        - data.product.original_price
        - data.price
        """
        candidates: list[Any] = []

        if isinstance(payload, dict):
            candidates.extend(
                [
                    payload.get("price"),
                    payload.get("product_price"),
                ]
            )
            data = payload.get("data")
            if isinstance(data, dict):
                candidates.extend(
                    [
                        data.get("price"),
                        data.get("product_price"),
                        data.get("current_price"),
                    ]
                )
                product = data.get("product")
                if isinstance(product, dict):
                    candidates.extend(
                        [
                            product.get("price"),
                            product.get("product_price"),
                            product.get("current_price"),
                            product.get("original_price"),
                        ]
                    )

        for candidate in candidates:
            normalized = ApiProvider._normalize_price(candidate)
            if normalized is not None:
                return normalized

        return None

    @staticmethod
    def _normalize_price(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value)
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if not cleaned:
            return None

        try:
            return float(cleaned)
        except ValueError:
            return None
