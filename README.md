# phone-price-tracker

Track iPhone (or other phone) prices using a clean, modular architecture.

## Architecture

- `config.json`: product definitions (`name`, `url`, `threshold`, plus optional API config)
- `providers/api_provider.py`: API provider (RapidAPI)
- `providers/scraper_provider.py`: scraper fallback provider (currently returns `None`)
- `price_tracker.py`: orchestration, CSV logging, and alerts

## Flow

1. Load products from `config.json`
2. For each product:
   - Try API provider first
   - If API fails, try scraper provider
3. Normalize provider output to:
   - `{ "price": float, "source": "api" }`
   - `{ "price": float, "source": "scraper" }`
4. Save run to `price_history.csv`
5. Print alert if price is below threshold

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variable

Set your RapidAPI key:

```bash
export RAPIDAPI_KEY="your_api_key_here"
```

## Run

```bash
python price_tracker.py
```
