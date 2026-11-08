"""
Original music bed + sound effects for the Flatline demo (155 s), synthesized
from scratch with numpy/scipy, so there is nothing to license.

Outputs (48 kHz stereo float WAV): music.wav, sfx.wav
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
T = 155.0
N = int(T * SR)
OUT = sys.argv[1] if len(sys.argv) > 1 else "mix-out"
rng = np.random.default_rng(7)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=-1)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=-1)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=-1)


def polyblep(t, dt):
    out = np.zeros_like(t)
    a = t < dt
    x = t[a] / dt
    out[a] = x + x - x * x - 1
    b = t > 1 - dt
    x = (t[b] - 1) / dt
    out[b] = x * x + x + x + 1
    return out


def saw(f, n, phase0=0.0):
    dt = f / SR
    t = (phase0 + dt * np.arange(n)) % 1.0
    return 2 * t - 1 - polyblep(t, dt)


def adsr(n, a, d, s, r, hold=None):
    """Envelope of n samples; release starts at `hold` seconds (default: n - r)."""
    t = np.arange(n) / SR
    total = n / SR
    hold = total - r if hold is None else hold
    env = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = t >= hold
    env[rel] *= np.exp(-(t[rel] - hold) / max(r / 4, 1e-6))
    return env


def place(buf, x, t0, gain=1.0):
    s = int(round(t0 * SR))
    if s >= buf.shape[-1]:
        return
    if s < 0:
        x = x[..., -s:]
        s = 0
    e = min(buf.shape[-1], s + x.shape[-1])
    buf[..., s:e] += gain * x[..., : e - s]


def stereo(x, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l * 1.414, x * r * 1.414])


def reverb_ir(seconds=1.8, decay=0.45, tone=5000):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-t / decay)
    ir = lp(ir, tone)
    ir[:, : int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return ir / np.sqrt(np.sum(ir**2, axis=1, keepdims=True))


IR = reverb_ir()
IR_SHORT = reverb_ir(0.9, 0.2, 7000)


def verb(x, ir=IR, wet=0.3):
    if x.ndim == 1:
        x = stereo(x)
    y = np.stack([fftconvolve(x[0], ir[0])[: x.shape[1]], fftconvolve(x[1], ir[1])[: x.shape[1]]])
    return x * (1 - wet) + y * wet


def db(g):
    return 10 ** (g / 20)


def norm_peak(x, peak_db):
    return x / (np.max(np.abs(x)) + 1e-9) * db(peak_db)


# ---------------------------------------------------------------- timeline
GROOVE_T0 = 18.4  # groove grid starts on the logo hit
BEAT = 0.5  # 120 BPM
BAR = 2.0
DROP = (99.2, 103.8)  # drums out for the REFUSED beat
FINAL_HIT = 150.2

# Checkout demo beats, measured on the recorded clips.
SFX_CLICKS = [27.2, 58.3]  # chaos Inject click, Approve click
SFX_BREACH = 38.0  # overview: checkout tile in breach
SFX_FOUND = 51.0  # "finds it"
SFX_BANNER = 53.6  # banner auto

TENSION = [[45, 57, 60, 64], [41, 57, 60, 65], [38, 57, 62, 65], [40, 56, 59, 64]]  # Am F Dm E
UPLIFT = [[41, 57, 60, 65], [36, 55, 60, 64], [43, 55, 59, 62], [45, 57, 60, 64]]  # F C G Am


def tension_chord(t):
    return TENSION[int(t // BAR) % 4]


def uplift_chord(t):
    return UPLIFT[int((t - GROOVE_T0) // BAR) % 4]


def section_brightness(t):
    """Pad filter cutoff over time (Hz)."""
    if t < 3.6:
        return 450
    if t < 8:
        return 600
    if t < GROOVE_T0:
        return 600 + (t - 8) / (GROOVE_T0 - 8) * 700
    if t < FINAL_HIT:
        return 1800
    return 2400


# ---------------------------------------------------------------- music
def make_pad():
    out = np.zeros((2, N))
    # tension: bars from 0 to 28.4 on a 2 s grid; uplift from 28.4 on its own grid
    starts = [(b * BAR, tension_chord(b * BAR)) for b in range(int(GROOVE_T0 // BAR))]
    starts[-1] = (starts[-1][0], starts[-1][1])
    t = GROOVE_T0
    while t < FINAL_HIT - 0.01:
        starts.append((t, uplift_chord(t)))
        t += BAR
    for i, (t0, chord) in enumerate(starts):
        t1 = starts[i + 1][0] if i + 1 < len(starts) else FINAL_HIT
        if t0 < GROOVE_T0 <= t1:
            t1 = GROOVE_T0
        dur = t1 - t0 + 0.7
        n = int(dur * SR)
        seg = np.zeros((2, n))
        for m in chord[1:]:
            for det, pan in [(-0.07, -0.7), (0.0, 0.0), (0.07, 0.7)]:
                f = mtof(m + det)
                seg += stereo(saw(f, n, rng.random()), pan) * 0.12
        cut = section_brightness(t0)
        seg = lp(seg, cut, 4 if t0 < GROOVE_T0 else 2)
        env = adsr(n, 0.35, 1.0, 1.0, 0.7, hold=t1 - t0)
        place(out, seg * env, t0)
    # final chord: C major, rings out
    n = int((T - FINAL_HIT) * SR)
    seg = np.zeros((2, n))
    for m in [48, 60, 64, 67, 72]:
        for det, pan in [(-0.08, -0.6), (0.08, 0.6)]:
            seg += stereo(saw(mtof(m + det), n, rng.random()), pan) * 0.1
    seg = lp(seg, 2200)
    t = np.arange(n) / SR
    seg *= np.minimum(1, t / 0.05) * np.exp(-t / 2.2)
    place(out, seg, FINAL_HIT)
    return verb(out, wet=0.35)


def make_bass():
    out = np.zeros(N)
    # tension: soft sub pulse on quarter notes (heartbeat-like), 0 -> 28.4
    t = 0.5
    while t < GROOVE_T0 - 0.3:
        root = tension_chord(t)[0]
        n = int(0.42 * SR)
        f = mtof(root)
        x = np.sin(2 * np.pi * f * np.arange(n) / SR) + 0.3 * saw(f, n)
        x = lp(x, 220)
        x *= adsr(n, 0.008, 0.18, 0.25, 0.1)
        g = 0.25 + 0.5 * min(1, t / 26)
        place(out, x, t, g)
        t += BEAT if t > 12 else BEAT * 2
    # groove: 8th-note bass
    t = GROOVE_T0
    while t < FINAL_HIT - 0.01:
        root = uplift_chord(t)[0]
        n = int(0.24 * SR)
        f = mtof(root)
        x = 0.7 * saw(f, n) + 0.6 * np.sin(2 * np.pi * f * np.arange(n) / SR)
        x = lp(x, 420)
        x *= adsr(n, 0.004, 0.1, 0.6, 0.06)
        place(out, x, t, 0.55)
        t += BEAT / 2
    # final sub
    n = int(4 * SR)
    x = np.sin(2 * np.pi * mtof(36) * np.arange(n) / SR) * np.exp(-np.arange(n) / SR / 1.5)
    place(out, x, FINAL_HIT, 0.6)
    return stereo(out)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.22)
    click = rng.standard_normal(n) * np.exp(-t / 0.002) * 0.25
    return lp(x + click, 3000)


def clap():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    env = np.zeros(n)
    for k in range(3):
        o = int(k * 0.011 * SR)
        env[o:] += np.exp(-(t[: n - o]) / (0.006 if k < 2 else 0.11))
    return bp(noise * env, 900, 3200)


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 7500, 4) * np.exp(-t / (0.09 if open_ else 0.022))
    return x


def make_drums():
    out = np.zeros((2, N))
    K, C = kick(), clap()
    # tension ticks: quiet 16th "clock" from 12 s, louder towards 28 s
    t = 12.0
    while t < GROOVE_T0 - 0.4:
        g = 0.05 + 0.12 * (t - 12) / 16
        place(out, stereo(hat(), 0.35 if int(t / 0.25) % 2 else -0.35), t, g)
        t += 0.25
    # groove
    t = GROOVE_T0
    i = 0
    while t < FINAL_HIT - 0.01:
        in_drop = DROP[0] - 0.05 <= t < DROP[1] - 0.05
        beat_in_bar = i % 4
        if not in_drop:
            place(out, stereo(K), t, 0.8)
            if beat_in_bar in (1, 3):
                place(out, verb(stereo(C), IR_SHORT, 0.35), t, 0.22)
            place(out, stereo(hat(), -0.3), t + BEAT / 2, 0.16)
            place(out, stereo(hat(), 0.3), t + BEAT / 4, 0.05)
            place(out, stereo(hat(), 0.3), t + 3 * BEAT / 4, 0.05)
            if beat_in_bar == 3 and (i // 4) % 2 == 1:
                place(out, stereo(hat(True), 0.2), t + BEAT / 2, 0.08)
        t += BEAT
        i += 1
    return out


def make_arp():
    out = np.zeros((2, N))
    t = GROOVE_T0
    step = 0
    pattern = [0, 1, 2, 1, 3, 2, 1, 2]
    while t < FINAL_HIT - 0.01:
        muted = (DROP[0] <= t < DROP[1]) or (72.0 <= t < 82.4)
        if not muted:
            chord = uplift_chord(t)[1:]
            notes = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 24]
            m = notes[pattern[step % 8]]
            n = int(0.2 * SR)
            x = saw(mtof(m), n) * np.exp(-np.arange(n) / SR / 0.07)
            x = lp(x, 2600)
            place(out, stereo(x, 0.25 if step % 2 else -0.25), t, 0.09)
        t += BEAT / 4
        step += 1
    # ping-pong dotted-eighth delay
    d = int(0.375 * SR)
    y = out.copy()
    for k in range(1, 4):
        g = 0.33**k
        src = out[(k + 1) % 2] if k % 2 else out[k % 2]
        tmp = np.zeros(N)
        tmp[d * k :] = src[: N - d * k]
        y[k % 2] += g * tmp
    return verb(y, wet=0.3)


def riser(dur, end_t, buf, gain, top=7000):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # sweep by crossfading 6 band-passed copies
    bands = np.geomspace(300, top, 7)
    x = np.zeros(n)
    pos = (t / dur) * (len(bands) - 2)
    for b in range(len(bands) - 1):
        w = np.clip(1 - np.abs(pos - b), 0, 1)
        x += bp(noise, bands[b], bands[b + 1]) * w
    x *= (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(200 * 2 ** (2 * t / dur)) / SR) * 0.15 * (t / dur) ** 2
    place(buf, verb(stereo(x + tone), wet=0.4), end_t - dur, gain)


def impact(buf, t0, gain, bright=True):
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    f = 35 + 40 * np.exp(-t / 0.15)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    crack = lp(rng.standard_normal(n), 1800 if bright else 700) * np.exp(-t / 0.25) * 0.5
    x = boom + crack
    if bright:
        shimmer = hp(rng.standard_normal(n), 6000) * np.exp(-t / 0.8) * 0.12
        x = x + shimmer
    place(buf, verb(stereo(x), wet=0.45), t0, gain)


# ---------------------------------------------------------------- sfx
def whoosh(buf, t_center, gain, dur=0.7, pan_dir=1):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    pos = t / dur
    lo = bp(noise, 300, 1200)
    hi = bp(noise, 1200, 5000)
    bell = np.sin(np.pi * pos) ** 2
    x = (lo * (1 - pos) + hi * np.sin(np.pi * pos)) * bell
    pan = (-1 + 2 * pos) * 0.8 * pan_dir
    st = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)]) * 1.4
    place(buf, verb(st, IR_SHORT, 0.3), t_center - dur * 0.6, gain)


def blip(f, dur=0.06, decay=0.025, shape="sine"):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if shape == "sine":
        x = np.sin(2 * np.pi * f * t)
    else:
        x = np.sign(np.sin(2 * np.pi * f * t)) * 0.5
        x = lp(x, 3000)
    return x * np.exp(-t / decay) * np.minimum(1, t / 0.002)


def bell(f, dur=1.4, decay=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (decay / r**0.5)) for r, a in [(1, 1), (2.0, 0.35), (3.01, 0.15), (4.2, 0.06)])
    return x * np.minimum(1, t / 0.003)


def make_sfx():
    s = np.zeros((2, N))
    # S1 (8 s): typing (0.3-1.3) and accelerating error ticks (cascade of 500s)
    t = 0.28
    while t < 1.33:
        n = int(0.012 * SR)
        x = bp(rng.standard_normal(n), 2000, 6000) * np.exp(-np.arange(n) / SR / 0.003)
        place(s, stereo(x, rng.uniform(-0.3, 0.3)), t, db(-30))
        t += rng.uniform(0.045, 0.08)
    f = 46  # frames
    k = 0
    while f < 100:
        tt = f / 30
        place(s, stereo(blip(1320 - 25 * min(k, 16), 0.07, 0.02, "square"), 0.2 if k % 2 else -0.2), tt, db(-27 + min(k, 12) * 0.45))
        f += max(2, round(15 * 0.78**k))
        k += 1
    riser(1.6, 3.6, s, db(-20), top=4000)
    impact(s, 3.6, db(-14), bright=False)
    # scene whooshes
    for tc in [8.0, 26.0, 71.0, 85.0, 107.0, 125.0, 140.0]:
        whoosh(s, tc, db(-24), pan_dir=1 if int(tc) % 2 else -1)
    impact(s, 15.25, db(-20), bright=False)  # "Noticed days later."
    riser(2.2, GROOVE_T0, s, db(-16))
    impact(s, GROOVE_T0, db(-12))  # Flatline logo
    for i, tt in enumerate([20.8, 21.0, 21.2]):  # chips
        n = int(0.05 * SR)
        tm = np.arange(n) / SR
        x = np.sin(2 * np.pi * np.cumsum(500 + 9000 * tm) / SR) * np.exp(-tm / 0.015)
        place(s, stereo(x, -0.4 + 0.4 * i), tt, db(-26))
    # Checkout demo (26-71)
    for tt in SFX_CLICKS:  # chaos Inject, Approve
        n = int(0.03 * SR)
        x = bp(rng.standard_normal(n), 2500, 7000) * np.exp(-np.arange(n) / SR / 0.002) + blip(1800, 0.03, 0.006)
        place(s, stereo(x, 0.15), tt, db(-22))
    place(s, stereo(blip(988, 0.16, 0.05, "square")), SFX_BREACH, db(-26))  # breach alert
    place(s, stereo(blip(784, 0.2, 0.07, "square")), SFX_BREACH + 0.15, db(-26))
    for i, m in enumerate([84, 88]):  # "finds it" sparkle
        place(s, verb(stereo(bell(mtof(m), 1.0, 0.35), -0.3 + 0.6 * i)), SFX_FOUND + i * 0.08, db(-28))
    place(s, verb(stereo(blip(1760, 0.2, 0.05))), SFX_BANNER, db(-30))  # banner auto
    for i, m in enumerate([72, 76, 79]):  # approve chime
        place(s, verb(stereo(bell(mtof(m + 12), 1.4, 0.45), -0.3 + 0.3 * i)), SFX_CLICKS[1] + 0.2 + i * 0.07, db(-24))
    for i, m in enumerate([72, 76, 79, 84]):  # Resolved! chime
        place(s, verb(stereo(bell(mtof(m + 12), 2.0, 0.7), -0.45 + 0.3 * i), wet=0.45), 63.4 + i * 0.075, db(-21))
    # How it works (71-85, the old 25 s animation at 1.79x)
    place(s, stereo(blip(1318, 0.18, 0.06) * 0.8), 73.69, db(-24))  # alert two-tone
    place(s, stereo(blip(1109, 0.25, 0.08) * 0.8), 73.77, db(-24))
    place(s, verb(stereo(lp(blip(90, 0.25, 0.08), 400))), 74.02, db(-16))  # incident card thud
    place(s, verb(stereo(lp(blip(70, 0.3, 0.09), 300))), 81.25, db(-16))  # policy gate thunk
    place(s, verb(stereo(blip(1568, 0.25, 0.06)), IR_SHORT, 0.3), 82.98, db(-28))  # executor active
    # Refund wave: REFUSED
    for k2 in range(2):
        n = int(0.16 * SR)
        tm = np.arange(n) / SR
        x = (np.sign(np.sin(2 * np.pi * 110 * tm)) + np.sign(np.sin(2 * np.pi * 116.5 * tm))) * 0.4
        x = lp(x, 1400) * np.minimum(1, tm / 0.004) * np.exp(-tm / 0.12)
        place(s, stereo(x), DROP[0] + k2 * 0.2, db(-17))
    place(s, verb(stereo(lp(blip(85, 0.3, 0.07), 500))), DROP[0] + 0.02, db(-14))  # stamp thud
    impact(s, 104.0, db(-22), bright=False)
    # Renewals: reminder auto, capture waits
    place(s, verb(stereo(blip(1760, 0.2, 0.05))), 115.4, db(-30))
    place(s, stereo(blip(660, 0.12, 0.04)), 117.6, db(-30))
    # Trust checklist ticks
    for tt in [125.8, 130.0, 132.2, 134.0]:
        place(s, verb(stereo(blip(1568, 0.08, 0.025) + 0.5 * blip(2350, 0.08, 0.02)), IR_SHORT, 0.25), tt + 0.2, db(-27))
    # Close
    riser(1.9, FINAL_HIT, s, db(-17))
    impact(s, FINAL_HIT, db(-13))
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    pad = make_pad()
    bass = make_bass()
    drums = make_drums()
    arp = make_arp()
    # sidechain pump from groove kicks on pad + bass
    pump = np.ones(N)
    t = GROOVE_T0
    m = int(0.25 * SR)
    shape = 1 - 0.45 * np.exp(-np.arange(m) / SR / 0.07)
    while t < FINAL_HIT - 0.01:
        if not (DROP[0] - 0.05 <= t < DROP[1] - 0.05):
            s0 = int(t * SR)
            pump[s0 : s0 + m] = np.minimum(pump[s0 : s0 + m], shape[: max(0, min(m, N - s0))])
        t += BEAT
    music = pad * 1.0 * pump + bass * 0.9 * pump + drums * 1.0 + arp * 1.0
    # master fades
    tt = np.arange(N) / SR
    music *= np.minimum(1, tt / 0.6) * np.clip((T - tt) / 0.8, 0, 1)
    music = norm_peak(music, -3)
    sfx = make_sfx()
    sfx *= np.clip((T - tt) / 0.5, 0, 1)
    sf.write(os.path.join(OUT, "music.wav"), music.T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(os.path.join(OUT, "sfx.wav"), sfx.T.astype(np.float32), SR, subtype="FLOAT")
    print("music peak", np.abs(music).max(), "sfx peak", np.abs(sfx).max())


if __name__ == "__main__":
    main()
