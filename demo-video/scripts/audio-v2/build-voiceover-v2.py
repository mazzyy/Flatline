"""
Excited, gap-free voiceover for the Flatline demo video (v2).

- Kokoro-82M via kokoro-onnx, voice am_fenrir with its prosody half pushed
  away from the average male voice (livelier, higher, wider intonation).
- Script rewritten to fill the 170 s timeline and react to on-screen beats.
- Long internal pauses tightened; extreme pitch peaks soft-limited.
- Writes per-line wavs, a 170 s raw mix and narration.json (timings for captions).

Needs: pip install kokoro-onnx soundfile numpy praat-parselmouth
Model files: kokoro-v1.0.onnx, voices-v1.0.bin (GitHub release thewh1teagle/kokoro-onnx model-files-v1.0)
"""
import json
import os
import sys

import numpy as np
import parselmouth
import soundfile as sf
from kokoro_onnx import Kokoro
from parselmouth.praat import call

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("KOKORO_DIR", HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "vo2-out")
SR = 24000
TOTAL = 170.0
BASE_SPEED = 1.1
MAX_SPEED = 1.3
PROSODY_PUSH = 1.0  # 0 = stock voice; >0 = livelier intonation

SCENE_STARTS = [0, 12, 28, 40, 65, 100, 125, 140, 155, 165]

# (absolute start s, text). Starts are anchored to on-screen beats.
LINES = [
    # S1 Hook: typing + cascade of 500s, then "Nobody is on call for revenue."
    (0.35, "Friday night. Checkout starts failing... one error, then ten, then a hundred!"),
    (5.3, "And nobody notices. Because nobody is on call for revenue!"),
    (8.8, "Shops monitor their servers... not their money."),
    # S2 Problem: counter climbs, "Noticed days later."
    (12.3, "A broken checkout. A refund wave. A failing renewal."),
    (15.6, "Every hour nobody notices, money quietly leaks away. Look at that number climb!"),
    (21.3, "And most merchants? They only find out days later, from a payout report, or an angry customer!"),
    # S3 Introducing
    (28.3, "That's why I built Flatline!"),
    (29.6, "An on-call SRE agent, for your PayPal revenue."),
    (32.6, "It detects, diagnoses, and fixes... safely."),
    (35.6, "Like a teammate who never sleeps, and never moves money without asking."),
    # S4 How it works
    (40.4, "Here's how it works. Flatline listens to PayPal webhooks and checkout telemetry."),
    (44.7, "The moment a metric breaks its baseline... boom! Incident open."),
    (48.2, "Four agents jump in. Triage scopes the damage."),
    (51.0, "The Diagnostician finds the root cause, reading PayPal data through MCP."),
    (56.0, "The Remediator proposes a fix."),
    (57.7, "Every proposal hits a policy proxy. Plain code, not a prompt!"),
    (61.6, "Agents read. Code decides. Only the executor writes!"),
    # S5 Demo 1: checkout
    (65.3, "Okay, let's break something! I'm shipping a bad currency config."),
    (69.0, "Euros, on a US-dollar shop. What could possibly go wrong?"),
    (72.3, "Checkouts start failing, and within seconds, the incident is open!"),
    (75.8, "And look! The shop already shows a warning banner."),
    (79.0, "Triage scopes it, and the Diagnostician goes hunting..."),
    (82.2, "Found it! Config version two set the wrong currency."),
    (85.3, "The banner? Already handled, automatically."),
    (88.2, "But rolling back the config? That needs me."),
    (90.9, "One click... approved!"),
    (94.2, "Failures drop right back to baseline, and the Verifier confirms it."),
    (97.8, "Resolved!"),
    # S6 Demo 2: refund wave
    (100.2, "Next up: a refund wave!"),
    (101.8, "One product, the Ethiopia Yirgacheffe, is behind most of the refunds."),
    (106.7, "So it proposes pausing sales of that product, and that waits for my approval."),
    (111.6, "Then it gets bold... and tries a bulk refund!"),
    (114.4, "Refused! Bulk refunds are forbidden, full stop."),
    (119.3, "The agent asked. The policy said no."),
    (121.8, "Agents can ask... but code decides!"),
    # S7 Renewals
    (125.3, "Now, four subscription renewals fail within an hour."),
    (128.4, "A payment reminder goes out automatically."),
    (131.0, "But capturing the outstanding balance? That waits for a human."),
    (134.5, "Small fixes run on their own. Money only moves with a human!"),
    # S8 Trust
    (140.3, "And it's built to be trusted. It only runs in the PayPal sandbox."),
    (145.0, "Agents never hold write credentials."),
    (147.2, "Unknown actions are forbidden."),
    (149.0, "And every single step lands in the audit log: who did what, and why."),
    (153.0, "Nothing happens in the dark."),
    # S9 Built with
    (155.3, "Built on PayPal's REST APIs, MCP server, and JavaScript SDK..."),
    (160.4, "with Google Gemini, Python, FastAPI and React."),
    # S10 Close
    (165.3, "Flatline. On call for your revenue!"),
]

PH_FIX = {"kənfˈɪɡ": "kˈɑːnfɪɡ", "jˈɜːɡɐʃˌɛf": "jˌɪɹɡətʃˈɛfeɪ"}


def scene_of(t):
    s = 0
    for i, st in enumerate(SCENE_STARTS):
        if t >= st - 1e-6:
            s = i
    return s


k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
MALES = ["am_michael", "am_puck", "am_fenrir", "am_echo", "am_eric", "am_liam", "am_onyx", "am_adam"]
_mean = np.mean([k.get_voice_style(n) for n in MALES], axis=0)
STYLE = k.get_voice_style("am_fenrir").copy()
STYLE[..., 128:] = STYLE[..., 128:] + PROSODY_PUSH * (STYLE[..., 128:] - _mean[..., 128:])


def phon(text):
    p = k.tokenizer.phonemize(text, "en-us")
    for a, b in PH_FIX.items():
        p = p.replace(a, b)
    return p


def frames_db(a, win):
    n = len(a) // win
    rms = np.sqrt(np.mean(a[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms / (np.max(rms) + 1e-12))


def trim(a, thr_db=-42, pad=0.025):
    win = int(0.01 * SR)
    db = frames_db(a, win)
    idx = np.where(db > thr_db)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] * win - int(pad * SR))
    e = min(len(a), (idx[-1] + 1) * win + int(pad * SR))
    return a[s:e]


def tighten_pauses(a, thr_db=-38, max_pause=0.32):
    """Shorten silent stretches longer than max_pause (keeps delivery flowing)."""
    win = int(0.01 * SR)
    db = frames_db(a, win)
    silent = db < thr_db
    out, i, n = [], 0, len(silent)
    keep = int(max_pause / 0.01)
    while i < n:
        if silent[i]:
            j = i
            while j < n and silent[j]:
                j += 1
            run = j - i
            if run > keep:
                half = keep // 2
                out.append(a[i * win : (i + half) * win])
                out.append(a[(j - (keep - half)) * win : j * win])
            else:
                out.append(a[i * win : j * win])
            i = j
        else:
            j = i
            while j < n and not silent[j]:
                j += 1
            out.append(a[i * win : j * win])
            i = j
    out.append(a[n * win :])
    return np.concatenate(out)


def limit_peaks(a, knee_st=10.5, ratio=0.45):
    """Soft-limit pitch excursions far above the speaker's median (avoid squeaky exclamations)."""
    snd = parselmouth.Sound(a.astype(np.float64), SR)
    manip = call(snd, "To Manipulation", 0.01, 60, 500)
    pt = call(manip, "Extract pitch tier")
    n = call(pt, "Get number of points")
    if n < 3:
        return a, 0
    fs = np.array([call(pt, "Get value at index", i + 1) for i in range(n)])
    med = np.median(fs)
    st = 12 * np.log2(fs / med)
    if st.max() <= knee_st:
        return a, 0
    ts = np.array([call(pt, "Get time from index", i + 1) for i in range(n)])
    st2 = np.where(st > knee_st, knee_st + (st - knee_st) * ratio, st)
    pt2 = call("Create PitchTier", "x", snd.xmin, snd.xmax)
    for t, s in zip(ts, st2):
        call(pt2, "Add point", float(t), float(med * 2 ** (s / 12)))
    call([pt2, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    return out.values[0].astype(np.float32), int((st > knee_st).sum())


def render(text, speed):
    a, sr = k.create(phon(text), voice=STYLE, speed=speed, is_phonemes=True)
    assert sr == SR
    return tighten_pauses(trim(a))


def main():
    os.makedirs(OUT, exist_ok=True)
    timeline = np.zeros(int(TOTAL * SR), dtype=np.float32)
    rows = []
    for i, (start, text) in enumerate(LINES):
        sc = scene_of(start)
        scene_end = SCENE_STARTS[sc + 1] if sc + 1 < len(SCENE_STARTS) else TOTAL
        nxt = LINES[i + 1][0] if i + 1 < len(LINES) else TOTAL
        limit = min(nxt - 0.12, scene_end + 0.25, TOTAL - 0.4) - start
        speed = BASE_SPEED
        a = render(text, speed)
        d = len(a) / SR
        if d > limit:
            speed = min(MAX_SPEED, speed * d / limit * 1.02)
            a = render(text, speed)
            d = len(a) / SR
        a, limited = limit_peaks(a)
        d = len(a) / SR
        over = d - limit
        sf.write(os.path.join(OUT, f"{i:02d}.wav"), a, SR)
        s0 = int(start * SR)
        seg = a[: max(0, min(len(a), len(timeline) - s0))]
        timeline[s0 : s0 + len(seg)] += seg
        rows.append(dict(i=i, scene=sc, start=round(start, 3), end=round(start + d, 3), dur=round(d, 3),
                         limit=round(limit, 2), speed=round(speed, 3), over=round(max(0, over), 2),
                         peaks_limited=limited, text=text))
        flag = "  <-- OVER" if over > 0.02 else ""
        print(f"{i:02d} {start:6.1f}s {d:5.2f}s / {limit:5.2f}s  x{speed:.2f}  {text[:70]}{flag}", flush=True)
    sf.write(os.path.join(OUT, "voice-raw.wav"), timeline, SR)
    with open(os.path.join(OUT, "narration.json"), "w") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    speech = sum(r["dur"] for r in rows)
    gaps = [rows[j + 1]["start"] - rows[j]["end"] for j in range(len(rows) - 1)] + [TOTAL - rows[-1]["end"], rows[0]["start"]]
    print(f"speech {speech:.1f}s = {speech / TOTAL * 100:.0f}%  gaps>2s: {sum(g > 2 for g in gaps)}  longest gap {max(gaps):.1f}s")


if __name__ == "__main__":
    main()
