#!/usr/bin/env python3
"""Track mobile phone prices using API-first with scraper fallback."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providers.api_provider import ApiProvider
from providers.scraper_provider import ScraperProvider


CONFIG_FILE = Path("config.json")
CSV_FILE = Path("price_history.csv")


@dataclass
class PriceRecord:
    timestamp_utc: str
    name: str
    site: str
    url: str
    threshold: float
    price: float | None
    source: str
    note: str


def load_products(config_path: Path = CONFIG_FILE) -> list[dict[str, Any]]:
    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    products = data.get("products", [])
    if not isinstance(products, list):
        raise ValueError("config.json must contain a list in 'products'")
    return products


def fetch_with_fallback(product: dict[str, Any], api: ApiProvider, scraper: ScraperProvider) -> PriceRecord:
    timestamp = datetime.now(timezone.utc).isoformat()
    name = str(product.get("name", "Unnamed Product"))
    site = str(product.get("site", "unknown"))
    url = str(product.get("url", ""))
    threshold = float(product.get("threshold", 0))

    api_result = api.get_price(product)
    if api_result is not None:
        return PriceRecord(
            timestamp_utc=timestamp,
            name=name,
            site=site,
            url=url,
            threshold=threshold,
            price=float(api_result["price"]),
            source="api",
            note="ok",
        )

    scraper_result = scraper.get_price(product)
    if scraper_result is not None:
        return PriceRecord(
            timestamp_utc=timestamp,
            name=name,
            site=site,
            url=url,
            threshold=threshold,
            price=float(scraper_result["price"]),
            source="scraper",
            note="ok",
        )

    return PriceRecord(
        timestamp_utc=timestamp,
        name=name,
        site=site,
        url=url,
        threshold=threshold,
        price=None,
        source="none",
        note="api_failed_and_scraper_failed",
    )


def append_csv(records: list[PriceRecord], csv_file: Path = CSV_FILE) -> None:
    exists = csv_file.exists()
    with csv_file.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not exists:
            writer.writerow(["timestamp_utc", "name", "site", "url", "price", "threshold", "source", "note"])

        for r in records:
            writer.writerow(
                [
                    r.timestamp_utc,
                    r.name,
                    r.site,
                    r.url,
                    "" if r.price is None else f"{r.price:.2f}",
                    f"{r.threshold:.2f}",
                    r.source,
                    r.note,
                ]
            )


def print_alerts(records: list[PriceRecord]) -> None:
    for r in records:
        if r.price is None:
            print(f"[WARN] {r.name}: price unavailable (source={r.source}, note={r.note})")
            continue

        print(f"[INFO] {r.name}: ₹{r.price:,.2f} via {r.source} (threshold ₹{r.threshold:,.2f})")
        if r.price < r.threshold:
            print(f"[ALERT] {r.name}: price dropped below threshold!")


def main() -> None:
    products = load_products()
    api_provider = ApiProvider()
    scraper_provider = ScraperProvider()

    records = [fetch_with_fallback(product, api_provider, scraper_provider) for product in products]
    append_csv(records)
    print_alerts(records)


if __name__ == "__main__":
    main()
