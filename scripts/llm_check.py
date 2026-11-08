#!/usr/bin/env python3
"""Check the models in .env before running the stack.

    python scripts/llm_check.py          # one short call to MODEL_FAST and MODEL_REASONING
    python scripts/llm_check.py --list   # models your Gemini key or local Ollama offers
    python scripts/llm_check.py --try gemini/gemini-2.5-flash gemini/gemini-3.5-flash

Works with any LiteLLM model string: gemini/<model>, ollama_chat/<model>,
azure/<deployment>. Needs `pip install -r requirements-live.txt`.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

import httpx

from flatline.config import settings
from flatline.llm.models import configure_litellm_env, live_complete, resolve_model

PROMPT = 'Reply with this JSON and nothing else: {"ok": true}'


def list_models() -> None:
    cfg = settings()
    if cfg.gemini_api_key:
        try:
            resp = httpx.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"pageSize": 200},
                headers={"x-goog-api-key": cfg.gemini_api_key},
                timeout=20,
            )
            resp.raise_for_status()
            names = [
                m["name"].split("/")[-1]
                for m in resp.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            print("Gemini models for your key:")
            for name in names:
                print(f"  gemini/{name}")
        except httpx.HTTPError as exc:
            print(f"Gemini: could not list models ({exc})")
    base = cfg.ollama_api_base or "http://localhost:11434"
    try:
        resp = httpx.get(f"{base}/api/tags", timeout=5)
        resp.raise_for_status()
        print(f"Ollama models at {base}:")
        for m in resp.json().get("models", []):
            print(f"  ollama_chat/{m['name']}")
    except httpx.HTTPError:
        print(f"Ollama: nothing answering at {base}")


def check(models: list[tuple[str, str]] | None = None) -> int:
    cfg = settings()
    if cfg.llm_mode != "live" and not models:
        print("Note: LLM_MODE is not live yet; the stack will keep using the playbook answers.")
    configure_litellm_env(cfg)
    if not models:
        models = [(kind, resolve_model(kind, cfg)) for kind in ("fast", "reasoning")]
    failed = 0
    for kind, model in models:
        started = time.perf_counter()
        try:
            answer = live_complete(model, PROMPT).strip()
        except ImportError:
            print("LiteLLM is missing: pip install -r requirements-live.txt")
            return 1
        except Exception as exc:
            failed += 1
            print(
                f"{kind:9s} {model}: FAILED {type(exc).__name__}: {str(exc).splitlines()[0][:300]}"
            )
            continue
        ms = int((time.perf_counter() - started) * 1000)
        print(f"{kind:9s} {model}: OK in {ms} ms, answered {answer[:80]}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="list available models")
    parser.add_argument("--try", dest="try_models", nargs="+", metavar="MODEL", help="test these")
    args = parser.parse_args()
    if args.list:
        list_models()
        return 0
    if args.try_models:
        return check([("try", m) for m in args.try_models])
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
