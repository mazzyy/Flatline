"""
Final mix: voice (mastered) + music bed (EQ-carved, ducked under voice) + SFX.
Inputs (relative to the folder passed as argv[1]): vo2-out/voice-raw.wav (24 kHz mono), mix-out/music.wav, mix-out/sfx.wav
Output: mix-out/final-mix.wav (48 kHz stereo), stems, and a loudness report.
"""
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, lfilter

SR = 48000
D = sys.argv[1] if len(sys.argv) > 1 else "."
meter = pyln.Meter(SR)


def peq(x, f0, gain_db, q=0.9, kind="peak"):
    """RBJ biquad (peak / highshelf / lowshelf)."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    alpha = np.sin(w) / (2 * q)
    c = np.cos(w)
    if kind == "peak":
        b = [1 + alpha * A, -2 * c, 1 - alpha * A]
        a = [1 + alpha / A, -2 * c, 1 - alpha / A]
    elif kind == "high":
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    else:
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return lfilter(b, a, x, axis=-1)


def compress(x, thr_db=-20, ratio=3.0, attack=0.005, release=0.09, makeup_db=0.0):
    mono = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=0)
    lvl = 20 * np.log10(mono + 1e-9)
    over = np.maximum(0, lvl - thr_db)
    target = -over * (1 - 1 / ratio)
    # smooth gain (attack/release) — vectorized via one-pole on the reduction signal
    a_att = np.exp(-1 / (attack * SR))
    a_rel = np.exp(-1 / (release * SR))
    g = np.empty_like(target)
    prev = 0.0
    for i in range(0, len(target), 64):  # block-wise for speed
        blk = target[i : i + 64].min()
        coef = a_att if blk < prev else a_rel
        prev = coef * prev + (1 - coef) * blk
        g[i : i + 64] = prev
    gain = 10 ** ((g + makeup_db) / 20)
    return x * gain


def envelope_db(x, win=0.01):
    w = int(win * SR)
    n = len(x) // w
    r = np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(1) + 1e-12)
    return np.repeat(20 * np.log10(r), w), w


def smooth(env, attack, release):
    out = np.empty_like(env)
    prev = env[0]
    aa, ar = np.exp(-1 / (attack * SR / 64)), np.exp(-1 / (release * SR / 64))
    for i in range(0, len(env), 64):
        v = env[i : i + 64].max()
        coef = aa if v > prev else ar
        prev = coef * prev + (1 - coef) * v
        out[i : i + 64] = prev
    return out


def limiter(x, ceiling_db=-1.5, release=0.05):
    c = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x), axis=0)
    need = np.minimum(1, c / (peak + 1e-9))
    # lookahead-free smoothing: take min over 2 ms windows then release
    w = int(0.002 * SR)
    n = len(need) // w
    blk = need[: n * w].reshape(n, w).min(1)
    blk = np.concatenate([blk, [1.0]])
    g = np.empty_like(blk)
    prev = 1.0
    ar = np.exp(-1 / (release * SR / w))
    for i, v in enumerate(blk):
        prev = v if v < prev else ar * prev + (1 - ar) * v
        g[i] = prev
    # 1-block lookahead
    g = np.minimum(g, np.concatenate([g[1:], [1.0]]))
    gain = np.repeat(g, w)[: x.shape[1]]
    gain = np.concatenate([gain, np.ones(x.shape[1] - len(gain))])
    return x * gain


def main():
    v24, sr = sf.read(f"{D}/vo2-out/voice-raw.wav", dtype="float64")
    assert sr == 24000
    v = resample_poly(v24, 2, 1)
    music, _ = sf.read(f"{D}/mix-out/music.wav", dtype="float64")
    sfx, _ = sf.read(f"{D}/mix-out/sfx.wav", dtype="float64")
    music, sfx = music.T, sfx.T
    N = music.shape[1]
    v = np.pad(v, (0, max(0, N - len(v))))[:N]

    # ---- voice chain
    v = sosfilt(butter(2, 75, "high", fs=SR, output="sos"), v)
    v = peq(v, 250, -2.0, 1.0)
    v = peq(v, 3200, 3.0, 0.8)
    v = peq(v, 9000, 1.5, 0.7, "high")
    v = compress(v, thr_db=-22, ratio=3.0, makeup_db=2.0)
    # a touch of room so it isn't bone-dry
    n_ir = int(0.5 * SR)
    t = np.arange(n_ir) / SR
    rng = np.random.default_rng(3)
    ir = rng.standard_normal(n_ir) * np.exp(-t / 0.09)
    ir = sosfilt(butter(2, 5000, "low", fs=SR, output="sos"), ir)
    ir /= np.sqrt((ir**2).sum())
    v = v + 0.07 * fftconvolve(v, ir)[:N]
    v *= 10 ** ((-16.0 - meter.integrated_loudness(v)) / 20)
    voice = np.stack([v, v])

    # ---- music: carve space for the voice, duck under it
    music = peq(music, 2600, -4.5, 0.8)
    music = peq(music, 8000, -2.5, 0.7, "high")
    music *= 10 ** ((-22.0 - meter.integrated_loudness(music.T)) / 20)
    env, _ = envelope_db(v)
    env = np.pad(env, (0, N - len(env)), constant_values=-120)
    active = np.clip((env + 45) / 12, 0, 1)  # 0 = silent, 1 = speaking
    duck_db = -9.0 * smooth(active, attack=0.04, release=0.45)
    music = music * 10 ** (duck_db / 20)

    sfx = sfx * 10 ** (-1.0 / 20)

    mix = voice + music + sfx
    loud = meter.integrated_loudness(mix.T)
    mix *= 10 ** ((-15.0 - loud) / 20)
    mix = limiter(mix, -1.5)
    sf.write(f"{D}/mix-out/final-mix.wav", mix.T.astype(np.float32), SR, subtype="FLOAT")
    g = 10 ** ((-15.0 - loud) / 20)
    sf.write(f"{D}/mix-out/stem-voice.wav", (voice * g).T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(f"{D}/mix-out/stem-music.wav", (music * g).T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(f"{D}/mix-out/stem-sfx.wav", (sfx * g).T.astype(np.float32), SR, subtype="FLOAT")

    # ---- report
    def lufs(x):
        try:
            return meter.integrated_loudness(x.T)
        except Exception:
            return float("nan")

    sp = active > 0.5
    vm = (voice * g)[:, sp]
    mm = (music * g)[:, sp]
    print(f"final integrated {meter.integrated_loudness(mix.T):.1f} LUFS, sample peak {20*np.log10(np.abs(mix).max()):.1f} dBFS")
    print(f"voice {lufs(voice*g):.1f} LUFS | music {lufs(music*g):.1f} LUFS | sfx {lufs(sfx*g):.1f} LUFS")
    vr = 10 * np.log10((vm**2).mean() / ((mm**2).mean() + 1e-12))
    print(f"voice-to-music ratio while speaking: {vr:.1f} dB")


if __name__ == "__main__":
    main()
