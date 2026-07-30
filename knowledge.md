# AI Agent Free Tier Monitor — Project Knowledge

## What This Project Is

A scraper + GUI tool for monitoring and comparing AI agent API free tiers, rate limits, and availability across providers (Google, Groq, Cerebras, OpenRouter, Mistral, Cohere, Cloudflare, NVIDIA, HuggingFace) and paid providers (OpenAI, Anthropic, xAI, DeepSeek). Built in 2026 with Indonesian (Bahasa) UI.

## File Structure

```
.
├── agents.json          # Single source of truth for agent database
├── dashboard.html       # Browser-based GUI (loads agents.json via fetch)
├── scraper.py           # Python async scraper (loads agents.json)
├── serve.py             # Local HTTP server for dashboard
├── test_scrapling.py    # Experimental scrapling scraper test
├── scrapling-env/       # Python venv for scrapling experimentation
└── README.md            # Project docs (Indonesian)
```

## Key Files

- **agents.json** — Single source of truth for all agent data (16 providers). Both dashboard.html and scraper.py read from this file.
- **dashboard.html** — Browser GUI. Loads agents.json via fetch. Requires local server (serve.py) due to CORS. Dark theme with green/yellow/red color coding.
- **scraper.py** — Async Python scraper using `aiohttp`. Loads agents.json at import time. Exports `run_scrape()` for programmatic use.
- **serve.py** — One-liner local HTTP server for dashboard. Run `python serve.py` then open `localhost:8080`.
- **test_scrapling.py** — Standalone script testing the `scrapling` library. Unrelated to main app.

## Commands

### Run the GUI
```bash
python serve.py           # default port 8080
python serve.py 3000      # custom port
# Then open http://localhost:8080 in browser
```

### Run the Python Scraper
```bash
pip install aiohttp
python scraper.py           # prints JSON to stdout
python scraper.py > hasil.json
```

### Import scraper programmatically
```python
from scraper import run_scrape

data = run_scrape()
free_active = [a for a in data["agents"] if a["type"] == "free" and a["result"]["status"] == "available"]
```

## Dependencies

- **Python scraper**: `aiohttp` (async HTTP)
- **Dashboard**: None (pure HTML/CSS/JS, fetches agents.json from serve.py)
- **test_scrapling.py**: `scrapling` (experimental, separate venv in `scrapling-env/`)

## Conventions

- **Language**: UI and comments in Bahasa Indonesia (Indonesian)
- **Color system**: 🟢 Green = free/active, 🟡 Yellow = flag/limited/slow, 🔴 Red = paid/error
- **Status values**: `"available"` (free+active), `"flag"` (yellow), `"unavailable"` (error), `"paid"` (requires credit card)
- **Data format**: `agents.json` is the single source of truth. Edit this file to add/change/remove agents.
- **Async pattern**: scraper uses `asyncio` + `aiohttp` with `TCPConnector(limit=20)`
- **Timeout**: 8 seconds per endpoint ping
- **Latency thresholds**: <600ms = good, 600-1500ms = acceptable, >1500ms = flag, >3000ms = severe flag

## Gotchas

- **Server required for dashboard**: dashboard.html uses fetch('./agents.json') which won't work with `file://` protocol. Must run `python serve.py` first.
- **CORS**: Dashboard uses `no-cors` mode for endpoint pings — response status is always 0 (opaque). Latency measurement still works but HTTP status codes are not available in browser.
- **Data editing**: To add/edit/remove agents, edit only `agents.json`. Both scraper.py and dashboard.html will pick up changes automatically.
- **scrapling-env**: Isolated venv for `scrapling` experiments. Not part of main scraper.
- **Endpoint validation**: Some endpoints return 401/403 for unauthorized — this is treated as "server active" (not an error).
- **Rate limits**: Limits data is manually curated from official docs as of July 2026. Check provider docs for current values.
