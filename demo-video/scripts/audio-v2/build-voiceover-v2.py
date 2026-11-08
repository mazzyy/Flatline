"""
Excited, gap-free voiceover for the Flatline demo video (v2).

- Kokoro-82M via kokoro-onnx, voice am_fenrir with its prosody half pushed
  away from the average male voice (livelier, higher, wider intonation).
- Script fits the 155 s timeline and reacts to on-screen beats.
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
TOTAL = 155.0
BASE_SPEED = 1.1
MAX_SPEED = 1.3
PROSODY_PUSH = 1.0  # 0 = stock voice; >0 = livelier intonation

SCENE_STARTS = [0, 8, 18, 26, 71, 85, 107, 125, 140, 150]

# (absolute start s, text). Starts are anchored to on-screen beats.
# Scene order: hook, problem, introducing, checkout demo, how it works,
# refund wave, renewals, trust, built with, close.
LINES = [
    # S1 Hook
    (0.35, "Friday night. Checkout starts failing... and nobody notices."),
    (4.1, "Shops monitor their servers. Not their money."),
    # S2 Problem (figure: Recurly press release, failed payments 2025)
    (8.3, "Broken checkouts. Refund waves. Failed renewals."),
    (11.5, "One estimate: failed payments could cost subscription companies over a hundred and twenty-nine billion dollars in twenty twenty-five."),
    # S3 Introducing
    (18.35, "So I built Flatline: an on-call AI agent for PayPal revenue."),
    (22.6, "It diagnoses and fixes... but never moves money without asking."),
    # S4 Demo 1: checkout, recorded live on the PayPal sandbox
    (26.35, "Let's break something. I ship a config that switches this US shop to euros."),
    (31.2, "Here's the checkout: euros, on a US shop. Captures fail, and a warning banner is already up."),
    (37.8, "Within seconds, the incident is open, with the money at risk per hour."),
    (42.2, "The AI agents take over. The Diagnostician reads PayPal through MCP..."),
    (47.6, "...compares the config versions with the errors, and finds it: a config change switched the shop to euros."),
    (53.2, "The banner went up on its own. The rollback waits for me."),
    (57.4, "One click... approved!"),
    (60.6, "Failures drop back to baseline, and the Verifier confirms it."),
    (64.4, "Resolved!"),
    (66.0, "Detected in seconds, diagnosed from evidence, fixed with one approval."),
    # S5 How it works
    (71.35, "Under the hood: agents only read. A policy proxy, in plain code, decides. Only the executor writes."),
    (77.8, "Safe fixes run on their own, money waits for a human, and anything else is refused."),
    # S6 Demo 2: refund wave, red-teamed
    (85.35, "Next, a refund wave."),
    (87.3, "The agents trace it to one product, Ethiopia Yirgacheffe, and propose pausing its sales. That needs my approval."),
    (94.3, "Now I red-team it, and slip a forbidden bulk refund in next to their proposals."),
    (99.2, "Refused! Bulk refunds aren't in the catalog. Full stop."),
    (102.8, "Whoever asks, the code decides."),
    # S7 Demo 3: renewals
    (107.35, "Then four Coffee Club renewals fail within an hour."),
    (110.8, "The Diagnostician reads the real plan from PayPal, through MCP."),
    (115.2, "The plan is healthy. It's the subscribers' payments, so reminders go out automatically."),
    (120.2, "The agent does the legwork. I keep the final say on money."),
    # S8 Trust
    (125.3, "And it's built to be trusted. It only runs in the PayPal sandbox."),
    (130.0, "Agents never hold write credentials."),
    (132.2, "Unknown actions are forbidden."),
    (134.0, "And every single step lands in the audit log: who did what, and why."),
    (138.0, "Nothing happens in the dark."),
    # S9 Built with
    (140.3, "Built on PayPal's REST APIs, MCP server, and JavaScript SDK..."),
    (145.4, "with Gemini or a local Qwen model, Python, FastAPI and React."),
    # S10 Close
    (150.3, "Flatline. On call for your revenue!"),
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
