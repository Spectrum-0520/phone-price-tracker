#!/usr/bin/env python3
"""Track mobile phone prices from Amazon India and Flipkart."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

# Hardcoded URLs and thresholds (as requested).
PRODUCTS = [
    {
        "site": "Amazon India",
        "url": "https://www.amazon.in/dp/B0DGHY9W9W",
        "threshold": 75000,
    },
    {
        "site": "Flipkart",
        "url": "https://www.flipkart.com/apple-iphone-16-black-128-gb/p/itm7c0281cd247be",
        "threshold": 75000,
    },
]

CSV_FILE = Path("price_history.csv")


@dataclass
class PriceResult:
    site: str
    url: str
    price_inr: Optional[float]
    threshold_inr: float
    fetched_at_utc: str
    note: str = ""


def _extract_json_ld_prices(html: str) -> list[str]:
    prices: list[str] = []
    scripts = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for script in scripts:
        script = script.strip()
        if not script:
            continue
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            offers = item.get("offers")
            if isinstance(offers, dict) and "price" in offers:
                prices.append(str(offers["price"]))
    return prices


def extract_price_text(html: str, site: str) -> Optional[str]:
    # 1) Try JSON-LD price first.
    prices = _extract_json_ld_prices(html)
    if prices:
        return prices[0]

    # 2) Site-specific regex selectors from raw HTML.
    patterns_by_site = {
        "Amazon India": [
            r'id="priceblock_ourprice"[^>]*>\s*₹?\s*([\d,]+(?:\.\d{1,2})?)',
            r'id="priceblock_dealprice"[^>]*>\s*₹?\s*([\d,]+(?:\.\d{1,2})?)',
            r'class="a-price-whole"[^>]*>\s*([\d,]+)',
        ],
        "Flipkart": [
            r'class="Nx9bqj\s+CxhGGd"[^>]*>\s*₹\s*([\d,]+(?:\.\d{1,2})?)',
            r'class="_30jeq3\s+_16Jk6d"[^>]*>\s*₹\s*([\d,]+(?:\.\d{1,2})?)',
            r'class="_30jeq3"[^>]*>\s*₹\s*([\d,]+(?:\.\d{1,2})?)',
        ],
    }

    for pattern in patterns_by_site.get(site, []):
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    # 3) Generic fallback.
    generic = re.search(r"(?:₹|Rs\.?\s?)([\d,]+(?:\.\d{1,2})?)", html)
    if generic:
        return generic.group(1)

    return None


def normalize_price(price_text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", price_text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_price(site: str, url: str, threshold: float) -> PriceResult:
    now_utc = datetime.now(timezone.utc).isoformat()
    request = Request(url, headers=HEADERS)

    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError) as exc:
        return PriceResult(site, url, None, threshold, now_utc, note=f"request_error: {exc}")

    price_text = extract_price_text(html, site)
    if not price_text:
        return PriceResult(site, url, None, threshold, now_utc, note="price_not_found")

    price = normalize_price(price_text)
    if price is None:
        return PriceResult(site, url, None, threshold, now_utc, note=f"price_parse_error: {price_text}")

    return PriceResult(site, url, price, threshold, now_utc)


def append_to_csv(results: list[PriceResult], csv_file: Path = CSV_FILE) -> None:
    exists = csv_file.exists()
    with csv_file.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not exists:
            writer.writerow(["timestamp_utc", "site", "url", "price_inr", "threshold_inr", "note"])

        for result in results:
            writer.writerow(
                [
                    result.fetched_at_utc,
                    result.site,
                    result.url,
                    "" if result.price_inr is None else f"{result.price_inr:.2f}",
                    f"{result.threshold_inr:.2f}",
                    result.note,
                ]
            )


def print_alerts(results: list[PriceResult]) -> None:
    for result in results:
        if result.price_inr is None:
            print(f"[WARN] {result.site}: unable to fetch price ({result.note})")
            continue

        print(f"[INFO] {result.site}: ₹{result.price_inr:,.2f} (threshold ₹{result.threshold_inr:,.2f})")
        if result.price_inr < result.threshold_inr:
            print(
                f"[ALERT] Price drop on {result.site}! Current ₹{result.price_inr:,.2f} "
                f"is below threshold ₹{result.threshold_inr:,.2f}."
            )


def main() -> None:
    results = [fetch_price(p["site"], p["url"], p["threshold"]) for p in PRODUCTS]
    append_to_csv(results)
    print_alerts(results)


if __name__ == "__main__":
    main()
