"""
AI Agent Free Tier Scraper - 2026
Mengecek ketersediaan endpoint AI gratis secara real-time
Warna: HIJAU = gratis + aktif | KUNING = terbatas/lambat | MERAH = berbayar/error

Agent database lives in agents.json — single source of truth.
"""

import asyncio
import aiohttp
import time
import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─────────────────────────────────────────────
# DATABASE AGENT — loaded from agents.json
# ─────────────────────────────────────────────
_AGENTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents.json")

def load_agents() -> list[dict]:
    """Load agent database from agents.json (single source of truth)."""
    try:
        with open(_AGENTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"agents.json not found at {_AGENTS_PATH}. "
            "This file is the single source of truth for the agent database."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"agents.json is invalid JSON: {e}")

AGENTS = load_agents()

# ─────────────────────────────────────────────
# SCRAPER ASYNC
# ─────────────────────────────────────────────
@dataclass
class ScrapeResult:
    agent_id: str
    status: str          # "available" | "flag" | "unavailable"
    latency_ms: Optional[int] = None
    http_code: Optional[int] = None
    error: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

async def ping_endpoint(session: aiohttp.ClientSession, agent: dict) -> ScrapeResult:
    url = agent["endpoint"]
    start = time.monotonic()
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=8),
            allow_redirects=True,
            ssl=False,
        ) as resp:
            ms = int((time.monotonic() - start) * 1000)
            code = resp.status
            # 200/401/403 = server aktif (auth error = server up)
            if code in (200, 401, 403, 404):
                if ms > 3000:
                    status = "flag"
                elif ms > 1500:
                    status = "flag"
                else:
                    status = "available"
                return ScrapeResult(agent["id"], status, ms, code)
            else:
                return ScrapeResult(agent["id"], "unavailable", ms, code,
                                    f"HTTP {code}")
    except asyncio.TimeoutError:
        ms = int((time.monotonic() - start) * 1000)
        return ScrapeResult(agent["id"], "flag", ms, None, "Timeout >8s")
    except Exception as e:
        ms = int((time.monotonic() - start) * 1000)
        return ScrapeResult(agent["id"], "unavailable", ms, None, str(e)[:60])

async def scrape_all(agents: list[dict]) -> list[ScrapeResult]:
    conn = aiohttp.TCPConnector(limit=20, ssl=False)
    headers = {
        "User-Agent": "AIAgentScraper/2.0 (research; contact: opensource@example.com)",
        "Accept": "application/json",
    }
    async with aiohttp.ClientSession(connector=conn, headers=headers) as session:
        tasks = [ping_endpoint(session, a) for a in agents]
        results = await asyncio.gather(*tasks)
    return list(results)

def run_scrape() -> dict:
    """Entry point utama — jalankan dari GUI atau CLI"""
    results = asyncio.run(scrape_all(AGENTS))
    result_map = {r.agent_id: r for r in results}

    output = []
    for agent in AGENTS:
        r = result_map.get(agent["id"])
        row = {**agent, "result": asdict(r) if r else {}}
        output.append(row)

    return {
        "scraped_at": datetime.now().isoformat(),
        "total": len(AGENTS),
        "free_count": sum(1 for a in AGENTS if a["type"] == "free"),
        "paid_count": sum(1 for a in AGENTS if a["type"] == "paid"),
        "agents": output,
    }

if __name__ == "__main__":
    print("🔍 Scraping AI agents...")
    data = run_scrape()
    print(json.dumps(data, indent=2, ensure_ascii=False))
