"""Synthesize the narration line by line and lay it out on a timeline (vo.json)."""
import json, os, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

K = os.environ.get("KOKORO_DIR", os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("VO_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
os.makedirs(OUT, exist_ok=True)
VOICE = sys.argv[1] if len(sys.argv) > 1 else "am_michael"
SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
SR = 24000

# (scene, id, gap before in seconds, spoken text, caption text)
LINES = [
 ("open", "line", 1.4, "This line is a coffee shop's revenue. Every beat is somebody paying.", None),
 ("open", "breaks", 1.2, "Friday evening, a config change goes out... and checkout breaks.", None),
 ("open", "monday", 1.9, "The servers are fine. Nobody finds out until Monday.", None),
 ("open", "oncall", 1.0, "We put people on call for servers. Nobody is on call for the money.", None),
 ("title", "built", 1.8, "So I built Flatline. An on-call engineer, for your PayPal revenue.", "So I built Flatline. An on-call engineer for your PayPal revenue."),
 ("break", "break", 1.0, "Let me break my own shop. One bad config, and this American store now charges in euros.", None),
 ("detect", "detect", 1.2, "Payments start failing. Within seconds, Flatline opens an incident, and puts a number on it: the money at risk, every hour.", None),
 ("agents", "agents", 0.9, "Then four A.I. agents go to work. One of them reads the real transactions from PayPal, through PayPal's own M.C.P. server.", "Then four AI agents go to work. One of them reads the real transactions from PayPal, through PayPal's own MCP server."),
 ("agents", "cause", 1.0, "And it finds the cause, with evidence. Not the bank. Not PayPal. Our own config change.", None),
 ("approve", "waits", 0.8, "The warning banner, it put up by itself. But the rollback waits for me.", None),
 ("approve", "click", 1.4, "One click.", None),
 ("approve", "back", 2.2, "And we're back.", None),
 ("recover", "stop", 2.4, "Most tools stop here. Incident resolved, everybody goes home.", None),
 ("recover", "six", 0.9, "But six people tried to buy coffee while we were down. That's a hundred and eight dollars, gone.", "But six people tried to buy coffee while we were down. That's $108, gone."),
 ("recover", "after", 0.8, "Flatline goes after it. It finds those six customers, and with one more approval, sends each of them a PayPal invoice, with an apology.", None),
 ("recover", "play", 2.6, "In this demo, I play the customers. Four of them pay.", None),
 ("recover", "seventy", 2.4, "Seventy-two dollars. Back.", "$72. Back."),
 ("recover", "code", 1.1, "And no A.I. writes those invoices. That part is plain code, because a model should never get to invent an amount.", "And no AI writes those invoices. That part is plain code, because a model should never get to invent an amount."),
 ("trust", "rule", 1.8, "That's the rule everywhere. The agents can only ask. Code decides.", None),
 ("trust", "refused", 0.7, "I tried to sneak in a bulk refund. Refused.", None),
 ("trust", "tiers", 0.7, "Safe fixes run on their own. Anything that moves money waits for a human. And refunds have a daily budget.", None),
 ("trust", "bench", 0.8, "And a benchmark attacks all of it. Thirty-four checks.", "And a benchmark attacks all of it. 34 checks."),
 ("close", "stack", 1.8, "Built on PayPal's sandbox, M.C.P. server, webhooks, and invoicing.", "Built on PayPal's sandbox, MCP server, webhooks and invoicing."),
 ("close", "oneline", 0.8, "It notices when your checkout breaks, fixes it, and gets the lost sales back.", None),
 ("close", "tag", 1.5, "Flatline. On call for your revenue.", None),
]
TAIL = 2.6  # after the last word

def trim(x, thr=0.004, pad=0.04):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx): return x
    a = max(0, idx[0] - int(pad * SR)); b = min(len(x), idx[-1] + int(pad * 3 * SR))
    return x[a:b]

k = Kokoro(f"{K}/kokoro-v1.0.onnx", f"{K}/voices-v1.0.bin")
t = 0.0; out = []; clips = []
for scene, lid, gap, text, cap in LINES:
    samples, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
    assert sr == SR
    x = trim(np.asarray(samples, dtype=np.float32))
    t += gap
    out.append({"scene": scene, "id": lid, "start": round(t, 3), "end": round(t + len(x) / SR, 3), "text": cap or text})
    clips.append((t, x)); t += len(x) / SR
total = t + TAIL
mix = np.zeros(int(total * SR) + SR, dtype=np.float32)
for start, x in clips:
    i = int(start * SR); mix[i:i + len(x)] += x
mix = mix[: int(total * SR)]
sf.write(f"{OUT}/voice-{VOICE}.wav", mix, SR)
scenes = {}
for l in out: scenes.setdefault(l["scene"], l["start"])
json.dump({"voice": VOICE, "total": round(total, 3), "lines": out}, open(f"{OUT}/vo-{VOICE}.json", "w"), indent=1)
print(VOICE, "total", round(total, 2), "speech", round(sum(l["end"] - l["start"] for l in out), 2))
for l in out: print(f'{l["start"]:7.2f} {l["end"]-l["start"]:5.2f} {l["scene"]:8s} {l["id"]}')
