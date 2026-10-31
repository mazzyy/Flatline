#!/usr/bin/env python3
"""
Launch a Cursor Cloud Agent to build Warden for Payments, then keep it working
unattended until every milestone in SPEC.md is done. Notifies you only at the end.

Uses the Cursor Cloud Agents API v0 (https://api.cursor.com/v0). Python 3.9+, stdlib only.

Before running:
  1. Create the GitHub repo (e.g. mazzyy/warden-pay) with an initial commit on main,
     and commit SPEC.md + AGENT_PROMPT.md to its root.
  2. Make sure Cursor's GitHub integration can access that repo.
  3. (Optional) Add sandbox / Azure secrets to your Cursor cloud agent environment.
  4. export CURSOR_API_KEY=...   (Cursor Dashboard -> API Keys)
     export NOTIFY_WEBHOOK_URL=... (optional: Slack incoming webhook or https://ntfy.sh/<topic>)

Usage:
  python launch_cursor_agent.py --repo https://github.com/mazzyy/warden-pay
  python launch_cursor_agent.py --list-models
  python launch_cursor_agent.py --repo ... --resume bc_abc123

Run it somewhere that stays on (a server, or tmux/nohup). If your laptop sleeps,
the cloud agent keeps working; re-run with --resume <agent id> to pick up the loop.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.cursor.com/v0"
STATE_FILE = Path(".warden_launcher_state.json")
ACTIVE = {"CREATING", "RUNNING", "PENDING", "QUEUED"}

CONTINUE_PROMPT = (
    "Continue building Warden for Payments. Re-read SPEC.md and PROGRESS.md, "
    "then work on the next milestone that is not DONE, following AGENT_PROMPT.md exactly. "
    "Do not ask questions. Keep going until all milestones M0-M10 are DONE or this run ends, "
    "and finish your final message with the required STATUS line."
)


# ---------------------------------------------------------------- HTTP helpers
def _auth_header(key: str) -> str:
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def call(method: str, path: str, key: str, body: dict | None = None, retries: int = 5):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(API + path, data=data, method=method)
        req.add_header("Authorization", _auth_header(key))
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode() or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(60, 5 * 2 ** attempt))
                continue
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(min(60, 5 * 2 ** attempt))
                continue
            raise RuntimeError(f"{method} {path} -> network error: {e}") from None
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------- notifications
def notify(message: str) -> None:
    print("\n" + "=" * 70 + "\n" + message + "\n" + "=" * 70, flush=True)
    url = os.environ.get("NOTIFY_WEBHOOK_URL")
    if not url:
        return
    try:
        if "ntfy" in url:
            req = urllib.request.Request(url, data=message.encode(), method="POST")
        else:  # Slack-compatible JSON
            req = urllib.request.Request(
                url, data=json.dumps({"text": message}).encode(), method="POST",
                headers={"Content-Type": "application/json"},
            )
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:  # never crash on notification failure
        print(f"(notification failed: {e})", flush=True)


# ---------------------------------------------------------------- state
def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log(msg: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg, flush=True)


# ---------------------------------------------------------------- agent ops
def launch(key: str, repo: str, ref: str, branch: str, prompt: str, model: str | None) -> dict:
    body = {
        "prompt": {"text": prompt},
        "source": {"repository": repo, "ref": ref},
        "target": {"autoCreatePr": True, "branchName": branch},
    }
    if model:
        body["model"] = model
    return call("POST", "/agents", key, body)


def last_assistant_text(key: str, agent_id: str) -> str:
    conv = call("GET", f"/agents/{agent_id}/conversation", key)
    msgs = [m for m in conv.get("messages", []) if m.get("type") == "assistant_message"]
    return msgs[-1].get("text", "") if msgs else ""


def parse_status(text: str) -> tuple[str, str]:
    m = re.findall(r"^\s*STATUS:\s*(COMPLETE|CONTINUE|BLOCKED)\b(.*)$", text, re.MULTILINE)
    if not m:
        return "UNKNOWN", ""
    kind, rest = m[-1]
    return kind, rest.strip(" -—:")


def wait_until_done(key: str, agent_id: str, poll: int) -> dict:
    while True:
        info = call("GET", f"/agents/{agent_id}", key)
        status = info.get("status", "UNKNOWN")
        if status not in ACTIVE:
            return info
        time.sleep(poll)


# ---------------------------------------------------------------- main loop
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="GitHub repo URL, e.g. https://github.com/mazzyy/warden-pay")
    ap.add_argument("--ref", default="main", help="base branch for the first launch")
    ap.add_argument("--branch", default="warden-pay/build", help="branch the agent works on")
    ap.add_argument("--model", default=None, help="model id from --list-models (default: your Cursor default)")
    ap.add_argument("--prompt-file", default="AGENT_PROMPT.md")
    ap.add_argument("--max-rounds", type=int, default=20, help="max follow-ups/relaunches before giving up")
    ap.add_argument("--poll", type=int, default=300, help="seconds between status checks")
    ap.add_argument("--resume", default=None, help="existing agent id to keep driving")
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("CURSOR_API_KEY")
    if not key:
        print("Set CURSOR_API_KEY first.", file=sys.stderr)
        return 2

    me = call("GET", "/me", key)
    log(f"Authenticated as {me.get('userEmail', '?')} (key: {me.get('apiKeyName', '?')})")

    if args.list_models:
        print(json.dumps(call("GET", "/models", key), indent=2))
        return 0
    if not args.repo:
        print("--repo is required.", file=sys.stderr)
        return 2

    prompt = Path(args.prompt_file).read_text()
    state = {"repo": args.repo, "branch": args.branch, "agents": [], "rounds": 0}

    if args.resume:
        agent_id = args.resume
        log(f"Resuming agent {agent_id}")
    else:
        info = launch(key, args.repo, args.ref, args.branch, prompt, args.model)
        agent_id = info["id"]
        log(f"Launched agent {agent_id} -> {info.get('target', {}).get('url', '')}")
    state["agents"].append(agent_id)
    save_state(state)

    while True:
        info = wait_until_done(key, agent_id, args.poll)
        status = info.get("status")
        pr_url = info.get("target", {}).get("prUrl", "")
        agent_url = info.get("target", {}).get("url", "")
        log(f"Agent {agent_id} stopped with status {status}")

        if status == "FINISHED":
            text = last_assistant_text(key, agent_id)
            kind, detail = parse_status(text)
            log(f"Reported STATUS: {kind} {detail}")

            if kind == "COMPLETE":
                notify(
                    "Warden for Payments build COMPLETE.\n"
                    f"PR: {pr_url or '(see agent page)'}\nAgent: {agent_url}\n"
                    f"Rounds used: {state['rounds']}\n\nFinal report:\n{text[-3000:]}"
                )
                return 0
            if kind == "BLOCKED":
                notify(
                    f"Warden for Payments build BLOCKED: {detail}\n"
                    f"PR: {pr_url}\nAgent: {agent_url}\n\nLast report:\n{text[-3000:]}"
                )
                return 1

        if state["rounds"] >= args.max_rounds:
            notify(
                f"Stopped after {args.max_rounds} rounds without STATUS: COMPLETE.\n"
                f"Last agent: {agent_url}\nPR: {pr_url}"
            )
            return 1

        state["rounds"] += 1
        save_state(state)

        if status == "FINISHED":
            try:
                call("POST", f"/agents/{agent_id}/followup", key, {"prompt": {"text": CONTINUE_PROMPT}})
                log(f"Round {state['rounds']}: sent follow-up to {agent_id}")
                time.sleep(30)
                continue
            except RuntimeError as e:
                log(f"Follow-up failed ({e}); relaunching on the work branch instead")

        # ERROR / EXPIRED / follow-up failure: start a fresh agent from the pushed branch.
        try:
            info = launch(key, args.repo, args.branch, args.branch, CONTINUE_PROMPT, args.model)
        except RuntimeError:
            info = launch(key, args.repo, args.ref, args.branch, prompt, args.model)
        agent_id = info["id"]
        state["agents"].append(agent_id)
        save_state(state)
        log(f"Round {state['rounds']}: relaunched as {agent_id}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. The cloud agent keeps running; use --resume <agent id> to continue.")
        sys.exit(130)
