"""
Human-sounding, upbeat voiceover for the Flatline demo video.

Kokoro-82M (open-source neural TTS, via kokoro-onnx) replaces macOS `say`.
Words match the burned-in captions in src/captions.ts exactly; only the
punctuation is tuned for delivery. Each line is generated, trimmed, given a
slightly wider / brighter pitch contour (PSOLA) for a more excited read,
time-fitted to its caption slot, then mixed onto a 170 s timeline.

Needs: pip install kokoro-onnx soundfile numpy praat-parselmouth
Model files (GitHub release thewh1teagle/kokoro-onnx model-files-v1.0):
  kokoro-v1.0.onnx, voices-v1.0.bin
"""
import json
import os
import subprocess
import sys

import numpy as np
import parselmouth
import soundfile as sf
from kokoro_onnx import Kokoro
from parselmouth.praat import call

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("KOKORO_DIR", HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "vo-out")
VOICE = os.environ.get("VOICE", "am_fenrir")
BASE_SPEED = 1.05
RANGE_K = 1.2   # widen pitch movement around the speaker's median
SHIFT_ST = 0.8  # lift pitch a little for energy
TOTAL = 170.0
SR = 24000

SCENES = [0, 12, 28, 40, 65, 100, 125, 140, 155, 165]

# (scene, from, to, voiced text, speed multiplier)
LINES = [
    (0, 0.6, 5.6, "Every online shop monitors its servers.", 1.0),
    (0, 6.0, 11.4, "Almost none... monitor their money!", 0.95),
    (1, 0.4, 6.2, "When a checkout breaks on a Friday evening, or refunds suddenly spike,", 1.0),
    (1, 6.4, 14.6, "most merchants find out days later... from a payout report, or an angry customer.", 1.0),
    (2, 0.8, 8.5, "This is Flatline! An on-call SRE agent, for your PayPal revenue!", 0.97),
    (3, 0.4, 4.4, "It listens to PayPal webhooks and checkout telemetry.", 1.0),
    (3, 4.6, 8.2, "When a metric breaks its baseline, four agents take over!", 1.0),
    (3, 8.4, 10.6, "Triage scopes the incident.", 1.0),
    (3, 10.8, 15.6, "The Diagnostician reads PayPal data through a read-only MCP server and finds the root cause.", 1.0),
    (3, 15.8, 18.0, "The Remediator proposes fixes.", 1.0),
    (3, 18.2, 22.2, "And every proposal goes through a policy proxy, written in plain code, not a prompt!", 1.0),
    (3, 22.4, 24.8, "Only the executor behind it can write.", 1.0),
    (4, 0.4, 4.2, "Let's break something! I ship a bad currency config.", 1.0),
    (4, 7.2, 12.4, "Checkouts start failing, and within seconds, an incident opens!", 1.0),
    (4, 14.4, 20.4, "The Diagnostician points to the exact config version that caused it, with evidence.", 1.0),
    (4, 20.6, 23.6, "A warning banner goes up automatically.", 1.0),
    (4, 23.8, 26.4, "The rollback needs my approval.", 1.0),
    (4, 27.2, 33.6, "I approve, failures stop, and the Verifier confirms recovery!", 1.0),
    (5, 0.4, 2.8, "Now, a refund wave!", 1.0),
    (5, 3.0, 9.0, "The agent finds one product behind most of the refunds, and proposes pausing it.", 1.0),
    (5, 10.0, 13.0, "It also tries a bulk refund...", 1.0),
    (5, 13.8, 16.6, "The policy says: no.", 0.9),
    (5, 19.8, 23.8, "Agents can ask. Code decides!", 0.95),
    (6, 0.4, 6.2, "For failed subscription renewals, a reminder goes out on its own.", 1.0),
    (6, 6.6, 12.4, "Capturing the outstanding balance waits for a human.", 1.0),
    (7, 0.4, 4.8, "It runs only in the PayPal sandbox,", 1.0),
    (7, 5.0, 8.6, "agents never hold write credentials,", 1.0),
    (7, 8.8, 13.4, "and every step is in the audit log!", 1.0),
    (8, 0.4, 8.4, "Built on PayPal's REST APIs, MCP server, and JavaScript SDK, with Azure-hosted models!", 1.0),
    (9, 0.3, 4.2, "Flatline! On call for your revenue!", 0.97),
]

# Small start nudges (s) so the two dense lines in S4 aren't rushed; captions still lead within 0.25 s
NUDGE = {8: -0.25, 9: 0.25, 10: -0.2, 11: 0.2}

# Phoneme fixes (espeak defaults -> how a US presenter says it)
PH_FIX = {"kənfˈɪɡ": "kˈɑːnfɪɡ"}

k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))


def phon(text):
    p = k.tokenizer.phonemize(text, "en-us")
    for a, b in PH_FIX.items():
        p = p.replace(a, b)
    return p


def synth(text, speed):
    a, sr = k.create(phon(text), voice=VOICE, speed=speed, is_phonemes=True)
    assert sr == SR
    return trim(a)


def trim(a, thr_db=-42, pad=0.03):
    win = int(0.01 * SR)
    n = len(a) // win
    if n == 0:
        return a
    rms = np.sqrt(np.mean(a[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (np.max(rms) + 1e-12))
    idx = np.where(db > thr_db)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] * win - int(pad * SR))
    e = min(len(a), (idx[-1] + 1) * win + int(pad * SR))
    return a[s:e]


def excite(a):
    snd = parselmouth.Sound(a.astype(np.float64), SR)
    manip = call(snd, "To Manipulation", 0.01, 60, 500)
    pt = call(manip, "Extract pitch tier")
    n = call(pt, "Get number of points")
    if n < 3:
        return a
    ts = np.array([call(pt, "Get time from index", i + 1) for i in range(n)])
    fs = np.array([call(pt, "Get value at index", i + 1) for i in range(n)])
    med = np.median(fs)
    st = np.clip(12 * np.log2(fs / med), -10, 12)  # guard against tracker octave errors
    new = med * 2 ** ((st * RANGE_K + SHIFT_ST) / 12)
    pt2 = call("Create PitchTier", "x", snd.xmin, snd.xmax)
    for t, f in zip(ts, new):
        call(pt2, "Add point", float(t), float(f))
    call([pt2, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    return out.values[0].astype(np.float32)


def atempo(a, factor):
    tmp_in, tmp_out = os.path.join(OUT, "_in.wav"), os.path.join(OUT, "_out.wav")
    sf.write(tmp_in, a, SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp_in, "-filter:a", f"atempo={factor:.4f}", tmp_out], check=True)
    b, _ = sf.read(tmp_out, dtype="float32")
    return b


def main():
    os.makedirs(OUT, exist_ok=True)
    timeline = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
    report = []
    starts = [SCENES[s] + f + NUDGE.get(j, 0) for j, (s, f, _, _, _) in enumerate(LINES)]
    for i, (scene, f, t, text, mult) in enumerate(LINES):
        start = starts[i]
        preferred = SCENES[scene] + t + 0.25 - start
        hard = (starts[i + 1] - 0.15 - start) if i + 1 < len(LINES) else (TOTAL - 0.4 - start)
        speed = BASE_SPEED * mult
        a = synth(text, speed)
        d = len(a) / SR
        # Too long: re-read faster (model speed is more natural than time-stretching)
        if d > preferred:
            speed = min(BASE_SPEED * 1.25, speed * d / preferred * 1.02)
            a = synth(text, speed)
            d = len(a) / SR
        a = excite(a)
        stretched = 1.0
        if d > hard:
            stretched = min(1.12, d / hard)
            a = atempo(a, stretched)
            d = len(a) / SR
        sf.write(os.path.join(OUT, f"{i:02d}.wav"), a, SR)
        s0 = int(start * SR)
        timeline[s0 : s0 + len(a)] += a
        report.append(dict(i=i, start=round(start, 2), dur=round(d, 2), preferred=round(preferred, 2),
                           hard=round(hard, 2), speed=round(speed, 3), atempo=round(stretched, 3),
                           overlap=d > hard + 0.01, text=text))
        print(f"{i:02d} {start:6.1f}s  {d:5.2f}s / slot {preferred:4.1f}s (max {hard:4.1f})  speed {speed:.2f}  {text[:60]}", flush=True)
    timeline = timeline[: int(TOTAL * SR)]
    raw = os.path.join(OUT, "voiceover-raw.wav")
    sf.write(raw, timeline, SR)
    with open(os.path.join(OUT, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("raw", raw)


if __name__ == "__main__":
    main()
