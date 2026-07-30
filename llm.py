#!/usr/bin/env python3
"""
Free LLM Hunter — CLI Agent
Chat with free AI providers from your terminal.

Usage:
    python llm.py chat --model gemini-2.5-flash
    python llm.py list
    python llm.py run --model groq/llama-3.3-70b
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error
from typing import Optional

# ── Load Provider Configs from agents.json ──────────────────────────

_AGENTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents.json")

# Provider API configs (base_url + api_key_env) — not in agents.json
_PROVIDER_API = {
    "google":      {"base_url": "https://generativelanguage.googleapis.com/v1beta", "api_key_env": "GOOGLE_API_KEY"},
    "groq":        {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "cerebras":    {"base_url": "https://api.cerebras.ai/v1", "api_key_env": "CEREBRAS_API_KEY"},
    "openrouter":  {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    "fireworks":   {"base_url": "https://api.fireworks.ai/inference/v1", "api_key_env": "FIREWORKS_API_KEY"},
    "together":    {"base_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},
    "deepseek":    {"base_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},
    "perplexity":  {"base_url": "https://api.perplexity.ai", "api_key_env": "PERPLEXITY_API_KEY"},
    "mistral":     {"base_url": "https://api.mistral.ai/v1", "api_key_env": "MISTRAL_API_KEY"},
    "cohere":      {"base_url": "https://api.cohere.ai/v1", "api_key_env": "COHERE_API_KEY"},
    "nvidia":      {"base_url": "https://integrate.api.nvidia.com/v1", "api_key_env": "NVIDIA_API_KEY"},
    "huggingface": {"base_url": "https://api-inference.huggingface.co/v1", "api_key_env": "HF_API_KEY"},
}

def load_providers() -> dict:
    """Load providers from agents.json and merge with API configs."""
    with open(_AGENTS_PATH, "r", encoding="utf-8") as f:
        agents = json.load(f)

    providers = {}
    for agent in agents:
        key = agent["id"].split("-")[0]  # e.g. "google-gemini-flash" → "google"
        api_cfg = _PROVIDER_API.get(key, {})
        if key not in providers:
            providers[key] = {
                "name": agent["org"],
                "base_url": api_cfg.get("base_url", ""),
                "api_key_env": api_cfg.get("api_key_env", ""),
                "models": [],
                "free": agent["type"] == "free",
                "requires_card": agent.get("requires_card", False),
                "signup_url": agent.get("signup_url", ""),
            }
        providers[key]["models"].extend(agent["models"])

    return providers

PROVIDERS = load_providers()

# ── Agent data (for endpoint pinging) ──────────────────────────────

def load_agents() -> list[dict]:
    """Load agent data from agents.json for endpoint pinging."""
    with open(_AGENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

AGENTS = load_agents()

# ── Endpoint Ping (reused from scraper) ─────────────────────────────
import time
import urllib.request
import urllib.error

def ping_endpoint(agent: dict) -> tuple[str, int]:
    """Ping an endpoint and return (status, latency_ms)."""
    url = agent["endpoint"]
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "llm-hunter/1.0")
        with urllib.request.urlopen(req, timeout=8) as resp:
            ms = int((time.monotonic() - start) * 1000)
            code = resp.status
            if code in (200, 401, 403, 404):
                status = "flag" if ms > 1500 else "available"
            else:
                status = "unavailable"
            return status, ms
    except urllib.error.URLError:
        ms = int((time.monotonic() - start) * 1000)
        return "flag" if ms > 3000 else "available", ms
    except Exception:
        ms = int((time.monotonic() - start) * 1000)
        return "unavailable", ms

# ── Colors ────────────────────────────────────────────────────────────

GREEN = "\033[1;32m"
CYAN = "\033[1;36m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ── Chat Completions (OpenAI-compatible) ─────────────────────────────

def chat_completion(
    provider: str,
    model: str,
    messages: list[dict],
    api_key: str,
    stream: bool = True,
) -> str:
    """Send chat completion request to OpenAI-compatible API."""
    p = PROVIDERS[provider]
    url = f"{p['base_url']}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": 4096,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # OpenRouter needs extra header
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/free-llm-hunter"
        headers["X-Title"] = "Free LLM Hunter CLI"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if stream:
                return _stream_response(resp)
            else:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"API error {e.code}: {body[:200]}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")


def _stream_response(resp) -> str:
    """Parse SSE streaming response."""
    full = ""
    for line in resp:
        line = line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                print(content, end="", flush=True)
                full += content
        except json.JSONDecodeError:
            continue
    print()
    return full


# ── Google API (non-OpenAI) ──────────────────────────────────────────

def google_chat(model: str, messages: list[dict], api_key: str) -> str:
    """Chat with Google Generative AI API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Convert messages to Google format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = json.dumps({
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 4096},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print(text)
            return text
    except Exception as e:
        raise Exception(f"Google API error: {e}")


# ── Commands ──────────────────────────────────────────────────────────

def cmd_list(args):
    """List all providers with availability status."""
    print(f"\n{BOLD}📡 Free LLM Hunter — Provider Status{RESET}\n")
    print(f"{DIM}Checking endpoints...{RESET}\n")

    # Ping all endpoints to get live status
    status_map = {}
    for agent in AGENTS:
        status, ms = ping_endpoint(agent)
        status_map[agent["id"]] = (status, ms)

    for key, p in PROVIDERS.items():
        # Get best status from agents of this provider
        provider_agents = [a for a in AGENTS if a["id"].startswith(key)]
        statuses = [status_map.get(a["id"], ("unknown", 0)) for a in provider_agents]
        best = "available" if any(s == "available" for s, _ in statuses) else (
            "flag" if any(s == "flag" for s, _ in statuses) else "unavailable"
        )

        # Status icons
        if best == "available":
            icon = f"{GREEN}●{RESET}"
            status_txt = f"{GREEN}ONLINE{RESET}"
        elif best == "flag":
            icon = f"{YELLOW}●{RESET}"
            status_txt = f"{YELLOW}SLOW{RESET}"
        else:
            icon = f"{RED}●{RESET}"
            status_txt = f"{RED}OFFLINE{RESET}"

        tier = f"{GREEN}FREE{RESET}" if p["free"] else f"{YELLOW}PAID{RESET}"
        env = p["api_key_env"]
        has_key = f"{GREEN}🔑{RESET}" if os.getenv(env) else f"{DIM}no-key{RESET}"

        print(f"  {icon} {BOLD}{key:<12}{RESET} {status_txt:<10} {tier}  {has_key}  {DIM}{p['name']}{RESET}")
        for m in p["models"]:
            print(f"                 {DIM}├── {m}{RESET}")

    print(f"\n{DIM}● = endpoint status | 🔑 = API key set{RESET}\n")


def cmd_chat(args):
    """Interactive chat with a model."""
    # Parse provider/model
    if "/" in args.model:
        provider, model = args.model.split("/", 1)
    else:
        # Auto-detect provider from model name
        provider = _detect_provider(args.model)
        model = args.model

    if provider not in PROVIDERS:
        print(f"{RED}Unknown provider: {provider}{RESET}")
        print(f"Use 'llm-hunter list' to see available providers.")
        sys.exit(1)

    p = PROVIDERS[provider]
    api_key = os.getenv(p["api_key_env"], "")

    if not api_key:
        print(f"{RED}API key not set for {p['name']}{RESET}")
        print(f"Set {p['api_key_env']} environment variable.")
        print(f"\nGet a free key at:")
        if provider == "google": print(f"  https://aistudio.google.com")
        elif provider == "groq": print(f"  https://console.groq.com")
        elif provider == "cerebras": print(f"  https://cloud.cerebras.ai")
        elif provider == "openrouter": print(f"  https://openrouter.ai")
        elif provider == "fireworks": print(f"  https://fireworks.ai")
        sys.exit(1)

    print(f"\n{CYAN}🤖 Free LLM Hunter{RESET} — {BOLD}{p['name']}{RESET}")
    print(f"{DIM}Model: {model} | Type 'exit' to quit{RESET}\n")

    messages = [{"role": "system", "content": args.system or "You are a helpful AI assistant."}]

    while True:
        try:
            user_input = input(f"{GREEN}You:{RESET} ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print(f"\n{DIM}Goodbye! 👋{RESET}")
                break

            messages.append({"role": "user", "content": user_input})
            print(f"{CYAN}AI:{RESET} ", end="", flush=True)

            if provider == "google":
                response = google_chat(model, messages, api_key)
            else:
                response = chat_completion(provider, model, messages, api_key, stream=True)

            messages.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print(f"\n\n{DIM}Goodbye! 👋{RESET}")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"\n{RED}Error: {e}{RESET}")


def cmd_run(args):
    """Run a single prompt (non-interactive)."""
    if "/" in args.model:
        provider, model = args.model.split("/", 1)
    else:
        provider = _detect_provider(args.model)
        model = args.model

    if provider not in PROVIDERS:
        print(f"{RED}Unknown provider: {provider}{RESET}")
        sys.exit(1)

    p = PROVIDERS[provider]
    api_key = os.getenv(p["api_key_env"], "")

    if not api_key:
        print(f"{RED}API key not set for {p['name']}{RESET}")
        sys.exit(1)

    prompt = args.prompt
    if not prompt:
        prompt = sys.stdin.read().strip()

    messages = [{"role": "user", "content": prompt}]
    print(f"{CYAN}AI:{RESET} ", end="", flush=True)

    if provider == "google":
        google_chat(model, messages, api_key)
    else:
        chat_completion(provider, model, messages, api_key, stream=True)


def _detect_provider(model: str) -> str:
    """Auto-detect provider from model name."""
    model_lower = model.lower()
    if "gemini" in model_lower: return "google"
    if "llama" in model_lower: return "groq"
    if "deepseek" in model_lower: return "deepseek"
    if "command" in model_lower: return "cerebras"
    if "mistral" in model_lower: return "mistral"
    if "sonar" in model_lower: return "perplexity"
    return "groq"


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="llm-hunter",
        description="Free LLM Hunter — Chat with free AI providers from your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  llm-hunter list                              # Show all providers
  llm-hunter chat --model gemini-2.5-flash     # Chat with Gemini
  llm-hunter chat --model groq/llama-3.3-70b
  llm-hunter run --model groq "What is AI?"
        """
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # list
    sub.add_parser("list", aliases=["ls"], help="List available providers and models")

    # chat
    chat_p = sub.add_parser("chat", aliases=["c"], help="Interactive chat with a model")
    chat_p.add_argument("-m", "--model", required=True, help="Model (e.g. gemini-2.5-flash or groq/llama-3.3-70b)")
    chat_p.add_argument("-s", "--system", help="System prompt")

    # run
    run_p = sub.add_parser("run", aliases=["r"], help="Run a single prompt")
    run_p.add_argument("-m", "--model", required=True, help="Model to use")
    run_p.add_argument("prompt", nargs="?", help="Prompt (or read from stdin)")

    args = parser.parse_args()

    if args.command in ("list", "ls"):
        cmd_list(args)
    elif args.command in ("chat", "c"):
        cmd_chat(args)
    elif args.command in ("run", "r"):
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
