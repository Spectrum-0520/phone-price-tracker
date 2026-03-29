# phone-price-tracker

Python tool to track iPhone 16 prices from Amazon India and Flipkart.

## Features
- Uses a hardcoded list of product URLs (Amazon India + Flipkart).
- Extracts current product price from page HTML.
- Appends each run to a `price_history.csv` file with UTC timestamp.
- Prints alert if the latest price is below per-product threshold.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python price_tracker.py
```

## Customize
Edit `PRODUCTS` in `price_tracker.py` to:
- update URLs
- update threshold values
- add/remove products
