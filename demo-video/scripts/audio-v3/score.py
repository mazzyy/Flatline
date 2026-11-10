"""Soundtrack for the Flatline film: voice, a score locked to the heartbeat, and sound effects.

Everything is synthesized here, so nothing in the mix is licensed from anyone.
    python score.py <vo.json> <voice.wav> <out_dir>
Writes mix.wav (voice + music + effects) and bed.wav (music + effects only).
"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly

VO, VOICE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 48000
vo = json.load(open(VO)); L = {l["id"]: l for l in vo["lines"]}
TOTAL = vo["total"]; N = int(TOTAL * SR)
cue = lambda i, d=0.0: L[i]["start"] + d
end = lambda i, d=0.0: L[i]["end"] + d
P = 0.92
BREAK_OPEN = end("breaks") - 1.0
REWIND = cue("built") - 1.5
BREAK_DEMO = cue("break") + 3.4
CLICK = end("click") + 0.45
REVIVE = CLICK + 0.35
RECOVERY_CLICK = cue("after") + 6.9
PAYMENTS = [end("play") + 0.25 + d for d in (0, 0.62, 1.24, 1.86)]
TAG = cue("tag") - 0.5
rng = np.random.default_rng(7)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)

class Bus:
    def __init__(self): self.b = np.zeros((N + SR * 6, 2), dtype=np.float64)
    def add(self, t, x, pan=0.0, gain=1.0):
        if t < 0: return
        i = int(t * SR); x = np.atleast_1d(x)
        if x.ndim == 1: x = np.stack([x * np.sqrt((1 - pan) / 2) * 1.414, x * np.sqrt((1 + pan) / 2) * 1.414], axis=1)
        j = min(len(self.b), i + len(x)); self.b[i:j] += x[: j - i] * gain

def tt(d): return np.arange(int(d * SR)) / SR
def adsr(d, a, r):
    n = int(d * SR); e = np.ones(n); na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na: e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr: e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e
def lp(x, f, order=2): return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f, order=2): return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)

def pad(notes, d, a=1.5, r=2.0, bright=0.5):
    """A warm string-like pad: a few detuned partials per note, slowly moving."""
    t = tt(d); out = np.zeros((len(t), 2))
    for m in notes:
        f = hz(m)
        for det, pan in ((-0.004, -0.6), (0.003, 0.6), (0.0, 0.0)):
            ph = rng.uniform(0, 6.28); v = np.zeros(len(t))
            for h in range(1, 7):
                v += np.sin(2 * np.pi * f * (1 + det) * h * t + ph * h) * (bright ** (h - 1)) / h
            v *= 1 + 0.08 * np.sin(2 * np.pi * 0.21 * t + ph)
            out[:, 0] += v * (1 - pan) / 2; out[:, 1] += v * (1 + pan) / 2
    return out * adsr(d, a, r)[:, None] / (len(notes) * 2.2)

def piano(m, d=3.0, hard=0.5):
    """A felt piano note: harmonics that die at different speeds, a soft hammer."""
    t = tt(d); f = hz(m); v = np.zeros(len(t))
    for h in range(1, 9):
        fh = f * h * np.sqrt(1 + 0.0004 * h * h)
        if fh > 9000: break
        v += np.sin(2 * np.pi * fh * t) * (hard ** (h - 1)) / h * np.exp(-t * (1.1 + 0.55 * h) * (f / 220) ** 0.35)
    v *= np.minimum(1, t / 0.006)
    return v * np.minimum(1, (d - t) / 0.2)

def bell(m, d=2.6):
    t = tt(d); f = hz(m)
    v = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * k) for r, a, k in ((1, 1, 2.2), (2.76, 0.45, 3.5), (5.4, 0.22, 5.5), (8.93, 0.1, 8)))
    return v * np.minimum(1, t / 0.003)

def pluck(m, d=0.42, cut=900):
    t = tt(d); f = hz(m)
    v = (np.sin(2 * np.pi * f * t) + 0.5 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-t * 18)) * np.exp(-t * 9)
    return lp(v, cut) * np.minimum(1, t / 0.004)

def beep(f=880.0, d=0.085):
    t = tt(d); return (np.sin(2 * np.pi * f * t) + 0.15 * np.sin(4 * np.pi * f * t)) * adsr(d, 0.006, 0.03)

def tone(d, f=880.0):
    t = tt(d); return np.sin(2 * np.pi * f * t) + 0.12 * np.sin(4 * np.pi * f * t)

def sub(d=1.6, f0=58, f1=34):
    t = tt(d); f = f1 + (f0 - f1) * np.exp(-t * 5)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6) * np.minimum(1, t / 0.004)

def noise_sweep(d, f0, f1, rise=True):
    n = int(d * SR); x = rng.standard_normal(n); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        k = i / n; f = f0 * (f1 / f0) ** k
        seg = x[max(0, i - blk): i + blk]
        y = sosfilt(butter(2, [f * 0.6, min(f * 1.6, SR / 2 - 100)], "band", fs=SR, output="sos"), seg)
        out[i: i + blk] = y[-min(blk, n - i):] if i else y[:blk]
    e = np.linspace(0, 1, n) ** 2 if rise else np.linspace(1, 0, n) ** 2
    return out * e

def tick(f=2600, d=0.03):
    t = tt(d); return hp(rng.standard_normal(len(t)), f) * np.exp(-t * 160)

def env(points):
    """Piecewise-linear gain over the whole film from (time, gain) points."""
    ts, gs = zip(*points); return np.interp(np.arange(len(music.b)) / SR, ts, gs)

music, fx, beeps = Bus(), Bus(), Bus()

# --- the heartbeat: one beep per spike while the shop is alive -------------------------
def spikes(o, a, b):
    s = o + 0.33 * P
    while s < a: s += P
    out = []
    while s < b: out.append(s); s += P
    return out
SP_A = spikes(0.35, 0.3, BREAK_OPEN)
SP_B = spikes(REWIND + 0.4, REWIND, BREAK_DEMO)
SP_C = [REVIVE + 0.05 + i * P for i in range(int((TOTAL - REVIVE) / P) + 1) if REVIVE + 0.05 + i * P < TOTAL - 0.4]
SP_C = [s for s in SP_C if not (PAYMENTS[0] - 0.4 < s < PAYMENTS[-1] + 0.6)]
for s in SP_A: beeps.add(s, beep(), gain=0.20)
for s in SP_B: beeps.add(s, beep(), gain=0.12)
for i, s in enumerate(SP_C):
    g = 0.2 if s < REVIVE + 3.2 else (0.15 if s > TAG else 0.022)
    beeps.add(s, beep(), gain=g)

# --- A. the shop is alive -------------------------------------------------------------
music.add(0, pad([38, 45, 50, 54, 57, 64], BREAK_OPEN + 0.3, a=2.5, r=0.5), gain=0.5)
for i, s in enumerate(SP_A):
    m = [69, 74, 78, 76, 74, 69, 71, 74, 78, 81, 76, 74, 78, 81][i % 14]
    music.add(s, piano(m, 3.2, 0.45), pan=(-0.3, 0.3)[i % 2], gain=0.11)

# --- B. flatline ----------------------------------------------------------------------
fx.add(BREAK_OPEN, sub(2.2), gain=0.75)
flat = tone(REWIND - BREAK_OPEN)
fx.add(BREAK_OPEN, lp(flat, 2400) * np.interp(tt(REWIND - BREAK_OPEN), [0, 0.02, 2.6, 5.5, REWIND - BREAK_OPEN - 0.2, REWIND - BREAK_OPEN], [0, 0.085, 0.07, 0.016, 0.012, 0]))
music.add(BREAK_OPEN + 0.8, pad([26, 38, 45, 53], REWIND - BREAK_OPEN - 0.3, a=3, r=1.2, bright=0.35), gain=0.62)
for k, m in enumerate([81, 77, 76, 74]):
    music.add(BREAK_OPEN + 3.2 + k * 3.68, piano(m, 4.5, 0.4), pan=0.25, gain=0.07)
    music.add(BREAK_OPEN + 3.2 + k * 3.68 + 1.84, piano(38, 5, 0.6), pan=-0.2, gain=0.1)
t0, t1 = cue("monday") + 0.2, end("monday") - 0.9   # the weekend goes by
s = t0
while s < t1:
    fx.add(s, tick(3200, 0.02), pan=rng.uniform(-0.5, 0.5), gain=0.05); s += 0.075

# --- Title: the same Friday again -----------------------------------------------------
fx.add(REWIND - 0.1, noise_sweep(1.5, 300, 5000), gain=0.16)
music.add(REWIND + 1.3, pad([38, 45, 50, 54, 57, 62, 66], BREAK_DEMO - REWIND - 1.0, a=0.5, r=0.6), gain=0.6)
fx.add(REWIND + 1.45, sub(1.4, 70, 40), gain=0.5)
for k, m in enumerate([50, 57, 62, 66, 69, 74, 78]):
    music.add(REWIND + 1.5 + k * 0.115, piano(m, 4, 0.5), pan=-0.4 + k * 0.13, gain=0.12)

# --- The incident: a pulse that tightens until the click ------------------------------
fx.add(BREAK_DEMO, sub(2.0), gain=0.8)
d = REVIVE - BREAK_DEMO
fx.add(BREAK_DEMO, lp(tone(d), 2400) * np.interp(tt(d), [0, 0.02, 1.4, 3, d - 0.5, d - 0.35], [0, 0.07, 0.05, 0.01, 0.01, 0]))
music.add(BREAK_DEMO + 0.6, pad([35, 42, 47, 50, 54], CLICK - BREAK_DEMO - 0.6, a=3, r=0.15, bright=0.4), gain=0.5)
g = BREAK_DEMO + 1.2; k = 0
while g < CLICK - 0.1:
    grow = (g - BREAK_DEMO) / (CLICK - BREAK_DEMO)
    music.add(g, pluck(35 if k % 8 else 47, 0.4, 500 + 900 * grow), gain=0.16 + 0.14 * grow)
    if g > cue("agents") and k % 2 == 0:
        music.add(g, pluck([66, 71, 74, 78, 74, 71][(k // 2) % 6], 0.5, 1800), pan=(-0.5, 0.5)[(k // 2) % 2], gain=0.035 + 0.05 * grow)
    if g > cue("waits"): fx.add(g + P / 4, tick(5000, 0.02), pan=0.3, gain=0.03 + 0.03 * grow)
    g += P / 2; k += 1
fx.add(CLICK - 1.5, noise_sweep(1.5, 400, 7000), gain=0.2)
fx.add(CLICK, tick(1800, 0.05), gain=0.5)
fx.add(BREAK_DEMO - 0.12, tick(1800, 0.05), gain=0.35)

# --- The line comes back --------------------------------------------------------------
fx.add(REVIVE, sub(2.4, 80, 38), gain=0.8)
fx.add(REVIVE, noise_sweep(1.8, 6000, 500, rise=False), gain=0.12)
music.add(REVIVE, pad([38, 45, 50, 54, 57, 62, 66, 69], cue("stop") - REVIVE + 2.5, a=0.25, r=3.5), gain=0.75)
for k, m in enumerate([50, 57, 62, 66, 69, 74, 78, 81, 86]):
    music.add(REVIVE + 0.05 + k * 0.1, piano(m, 4.5, 0.5), pan=-0.45 + k * 0.11, gain=0.14)

# --- "Most tools stop here": almost nothing, then six losses --------------------------
music.add(cue("stop") + 1.5, pad([45, 57], cue("six") - cue("stop"), a=2, r=2, bright=0.3), gain=0.35)
music.add(cue("six") - 0.3, pad([35, 42, 47, 50], cue("after") - cue("six") + 2.6, a=1.2, r=2.4, bright=0.4), gain=0.55)
for i, m in enumerate([66, 64, 62, 61, 59, 54]):
    music.add(cue("six") + 0.5 + i * 0.28, piano(m, 3.5, 0.5), pan=-0.4 + i * 0.16, gain=0.13)

# --- Recovery, guardrails and the close: one progression locked to the heartbeat ------
CH = [[43, 50, 55, 59, 62], [38, 45, 50, 54, 57], [45, 52, 57, 61, 64], [35, 42, 47, 50, 54]]  # G D A Bm
ARP = [[67, 71, 74, 79], [66, 69, 74, 78], [64, 69, 73, 76], [66, 71, 74, 78]]
g0 = REVIVE + 0.05
first = int(np.ceil((cue("after") + 2.0 - g0) / (4 * P)))
bars = [(g0 + i * 4 * P, i % 4) for i in range(first, int((TAG - g0) / (4 * P)) + 1)]
arp_gain = lambda t: np.interp(t, [cue("after"), RECOVERY_CLICK, PAYMENTS[0], cue("seventy") + 2, cue("code"), cue("rule"), cue("bench"), cue("stack"), cue("oneline"), TAG], [0.03, 0.06, 0.09, 0.1, 0.03, 0.045, 0.06, 0.07, 0.1, 0.1])
bass_gain = lambda t: np.interp(t, [cue("after"), RECOVERY_CLICK, cue("seventy"), cue("code"), cue("rule"), cue("stack"), TAG], [0.0, 0.1, 0.2, 0.08, 0.14, 0.18, 0.2])
for t, c in bars:
    if t >= TAG: break
    music.add(t - 0.3, pad(CH[c], 4 * P + 1.2, a=0.7, r=1.3), gain=0.5)
    for k in range(8):
        s = t + k * P / 2
        music.add(s, piano(ARP[c][(k * 3) % 4] + (12 if k % 4 == 3 else 0), 2.2, 0.42), pan=(-0.45, 0.45, -0.15, 0.15)[k % 4], gain=arp_gain(s))
        music.add(s, pluck(CH[c][0], 0.42, 700), gain=bass_gain(s) * (1.0 if k % 2 == 0 else 0.55))

fx.add(RECOVERY_CLICK, tick(1800, 0.05), gain=0.5)
fx.add(RECOVERY_CLICK + 0.35, noise_sweep(1.1, 900, 5000), gain=0.11)
for i in range(6): fx.add(RECOVERY_CLICK + 0.5 + i * 0.16 + 0.55, tick(900, 0.06), pan=-0.5 + i * 0.2, gain=0.22)
for i, p in enumerate(PAYMENTS):                      # four customers pay
    beeps.add(p, beep(880 * 2 ** ([0, 4, 7, 12][i] / 12), 0.11), gain=0.2)
    fx.add(p, bell([74, 78, 81, 86][i], 3.2), pan=-0.3 + i * 0.2, gain=0.17)
    fx.add(p, sub(0.6, 90, 55), gain=0.2)
music.add(cue("seventy") - 0.1, pad([38, 50, 57, 62, 66, 69, 74], 5.5, a=0.35, r=3.2), gain=0.6)
fx.add(cue("seventy") - 0.1, sub(2.2, 70, 36), gain=0.6)
for k, m in enumerate([62, 66, 69, 74, 78, 81, 86]):
    music.add(cue("seventy") + k * 0.09, piano(m, 4.5, 0.5), pan=-0.4 + k * 0.13, gain=0.11)

fx.add(cue("refused") + 2.55, sub(1.2, 95, 42), gain=0.75)   # the stamp
fx.add(cue("refused") + 2.55, lp(rng.standard_normal(int(0.12 * SR)) * np.exp(-tt(0.12) * 40), 1400), gain=0.5)
b0, b1 = cue("bench") + 1.2, cue("bench") + 4.9               # 34 checks light up
for i in range(34):
    fx.add(b0 + (b1 - b0) * i / 33, beep(520 * 2 ** (i / 34), 0.045), pan=-0.5 + i / 34, gain=0.05)
fx.add(b1 + 0.05, bell(86, 2.5), gain=0.14)
for dt in (0.25, 2.45, 3.25):                                 # notices, fixes, gets the lost sales back
    fx.add(cue("oneline") + dt, sub(0.9, 80, 45), gain=0.38)

music.add(TAG, pad([26, 38, 45, 50, 54, 57, 62, 66, 69], TOTAL - TAG + 1.5, a=0.5, r=4.5), gain=0.85)
fx.add(TAG, sub(2.6, 75, 34), gain=0.7)
for k, m in enumerate([50, 57, 62, 66, 69, 74, 78, 81, 86]):
    music.add(TAG + 0.05 + k * 0.11, piano(m, 6, 0.5), pan=-0.45 + k * 0.11, gain=0.14)
for dt in (cue("stop") - 1.2, cue("rule") - 0.9, cue("stack") - 0.9, cue("detect") - 0.5, cue("agents") - 0.6):
    fx.add(dt, noise_sweep(0.9, 500, 3500), gain=0.07)

# --- space, the voice, and the mix ----------------------------------------------------
ir_t = tt(2.8); ir = lp(rng.standard_normal((len(ir_t), 2)) * np.exp(-ir_t * 2.4)[:, None], 5200); ir[: int(0.012 * SR)] = 0
def wet(x, amt):
    w = np.stack([fftconvolve(x[:, i], ir[:, i])[: len(x)] for i in (0, 1)], axis=1)
    return x + w * amt * 0.02
mus = wet(music.b, 1.0) * 0.21
mus *= env([(0, 1), (cue("stop") + 1.2, 1), (cue("stop") + 2.4, 0.6), (cue("six"), 1), (TOTAL, 1)])[:, None]
sfx = wet(fx.b, 0.6) * 0.47 + wet(beeps.b, 0.5) * 0.8

v, vsr = sf.read(VOICE); assert vsr == 24000
v = resample_poly(v, 2, 1); v = hp(v, 75)
v = v + 0.35 * sosfilt(butter(2, [2500, 5500], "band", fs=SR, output="sos"), v)          # presence
win = int(0.01 * SR); rms = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, "same") + 1e-9)
thr = 0.09; gain = np.where(rms > thr, (thr / rms) ** 0.55, 1.0)                           # gentle compression
gain = np.convolve(gain, np.ones(int(0.03 * SR)) / int(0.03 * SR), "same"); v = v * gain
v = v / np.max(np.abs(v)) * 0.82
voice = np.zeros((len(mus), 2)); voice[: len(v)] = np.stack([v, v], axis=1)[: len(mus)]
room_t = tt(0.5); room = lp(rng.standard_normal((len(room_t), 2)) * np.exp(-room_t * 11)[:, None], 6000); room[: int(0.004 * SR)] = 0
voice_wet = np.stack([fftconvolve(voice[:, i], room[:, i])[: len(voice)] for i in (0, 1)], axis=1)
voice = voice + voice_wet * 0.012

# Duck the score under the voice.
lvl = np.sqrt(np.convolve(voice[:, 0] ** 2, np.ones(int(0.25 * SR)) / int(0.25 * SR), "same"))
duck = 1 - 0.56 * np.clip(lvl / 0.05, 0, 1)
duck = np.convolve(duck, np.ones(int(0.3 * SR)) / int(0.3 * SR), "same")
bed_full = mus + sfx
mix = mus * duck[:, None] + sfx * (0.75 + 0.25 * duck[:, None]) + voice

fade = np.ones(len(mix)); n_out = int(1.6 * SR); fade[N - n_out: N] = np.cos(np.linspace(0, np.pi / 2, n_out)) ** 2; fade[N:] = 0
for name, x in (("mix", mix), ("bed", bed_full)):
    x = (x * fade[:, None])[:N]; x = np.tanh(x * 1.15) / 1.15
    sf.write(f"{OUT}/{name}.wav", (x / max(1.0, np.max(np.abs(x)) / 0.97)).astype(np.float32), SR)
    print(name, "peak", round(float(np.max(np.abs(x))), 3), "rms", round(float(np.sqrt(np.mean(x ** 2))), 4))
w = 5 * SR
for nm, x in (("music", mus * duck[:, None]), ("sfx", sfx), ("voice", voice)):
    print(nm.ljust(6), " ".join(f"{int(1000 * np.sqrt(np.mean(x[i:i + w] ** 2))):3d}" for i in range(0, N, w)))
print("music rms", round(float(np.sqrt(np.mean(mus[:N] ** 2))), 4), "sfx rms", round(float(np.sqrt(np.mean(sfx[:N] ** 2))), 4), "voice rms", round(float(np.sqrt(np.mean(voice[:N] ** 2))), 4))
