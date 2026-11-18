#!/usr/bin/env python3
"""Synthesize all TuxoFlood sound effects and music loops from code.

Everything this script produces is original work for TuxoFlood, released under
CC0 1.0 (public domain dedication). Requires numpy; music is encoded to OGG
Vorbis with ffmpeg (libvorbis).

    python3 tools/make_sounds.py
"""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parent.parent / "tuxoflood" / "assets"
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ basics
def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def env(n: int, a=0.005, d=0.1, s=0.0, r=0.05, dur=None) -> np.ndarray:
    """Linear attack, exponential-ish decay to sustain, linear release."""
    t = np.arange(n) / SR
    total = n / SR if dur is None else dur
    e = np.ones(n)
    e[t < a] = t[t < a] / max(a, 1e-6)
    after = t >= a
    e[after] = s + (1 - s) * np.exp(-(t[after] - a) / max(d, 1e-6))
    rel_start = max(0.0, total - r)
    rel = t >= rel_start
    e[rel] *= np.clip(1 - (t[rel] - rel_start) / max(r, 1e-6), 0, 1)
    return e


def sine(f, t, phase=0.0):
    return np.sin(2 * np.pi * f * t + phase)


def tri(f, t):
    return 2 * np.abs(2 * ((f * t) % 1.0) - 1) - 1


def soft_square(f, t, harmonics=7):
    out = np.zeros_like(t)
    for k in range(1, harmonics * 2, 2):
        out += np.sin(2 * np.pi * f * k * t) / k
    return out * (4 / np.pi) * 0.6


def sweep(f0, f1, t, curve="exp"):
    dur = t[-1] if len(t) else 1
    if curve == "exp":
        f = f0 * (f1 / f0) ** (t / max(dur, 1e-6))
    else:
        f = f0 + (f1 - f0) * t / max(dur, 1e-6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def lowpass(x, alpha=0.2):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def mix_at(buf, sig, start_s):
    i = int(start_s * SR)
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i]


def normalize(x, peak=0.85):
    m = np.max(np.abs(x)) or 1.0
    return x * (peak / m)


# ------------------------------------------------------------ instruments
def bell(midi, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(midi)
    x = sine(f, t) + 0.35 * sine(2 * f, t) * np.exp(-t * 6) + 0.18 * sine(3.01 * f, t) * np.exp(-t * 9)
    return vel * x * env(len(t), a=0.003, d=dur * 0.35, r=min(0.05, dur * 0.3))


def pluck(midi, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(midi)
    x = 0.7 * tri(f, t) + 0.3 * sine(2 * f, t) * np.exp(-t * 8)
    return vel * x * env(len(t), a=0.004, d=dur * 0.45, s=0.0, r=0.04)


def lead(midi, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(midi) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 4, 0, 1))  # gentle vibrato
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    return vel * x * env(len(t), a=0.015, d=0.25, s=0.55, r=min(0.08, dur * 0.4))


def bass(midi, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(midi)
    x = sine(f, t) + 0.25 * sine(2 * f, t) + 0.08 * tri(f, t)
    return vel * x * env(len(t), a=0.006, d=0.22, s=0.35, r=0.05)


def pad(midis, dur, vel=1.0):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for m in midis:
        f = hz(m)
        x += sine(f * 1.002, t) + sine(f * 0.998, t) + 0.2 * sine(2 * f, t)
    x /= max(1, len(midis))
    return vel * x * env(len(t), a=dur * 0.3, d=10, s=1.0, r=dur * 0.35)


def kick(vel=1.0):
    t = t_axis(0.18)
    return vel * sweep(140, 48, t) * env(len(t), a=0.002, d=0.07, r=0.03)


def hat(vel=1.0, dur=0.05):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    hp = noise - lowpass(noise, 0.35)
    return vel * hp * env(n, a=0.001, d=dur * 0.3, r=0.01)


def shaker(vel=1.0):
    n = int(0.09 * SR)
    noise = rng.standard_normal(n)
    hp = noise - lowpass(noise, 0.25)
    return vel * hp * env(n, a=0.02, d=0.03, r=0.02)


# ---------------------------------------------------------------- effects
def noise_burst(dur, alpha=0.3, hp=False):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    lp = lowpass(x, alpha)
    return x - lp if hp else lp


def sfx_click():
    t = t_axis(0.045)
    return 0.5 * sine(1500, t) * env(len(t), a=0.001, d=0.012, r=0.01)


def sfx_hover():
    t = t_axis(0.03)
    return 0.22 * sine(2300, t) * env(len(t), a=0.001, d=0.008, r=0.01)


def bubble(f0, dur=0.09, vel=1.0):
    """A water bubble: short sine with a fast upward pitch glide."""
    t = t_axis(dur)
    f = f0 * (1 + 1.6 * t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return vel * np.sin(ph) * env(len(t), a=0.003, d=dur * 0.4, r=0.02)


def sfx_flood():                      # a colour pours over the region: soft splash + bubbles
    out = np.zeros(int(0.42 * SR))
    x = noise_burst(0.32, 0.08)
    t = np.arange(len(x)) / SR
    mix_at(out, 1.2 * x * np.sin(np.pi * t / t[-1]) ** 2, 0.0)
    for i, f in enumerate((420, 560, 500, 700)):
        mix_at(out, bubble(f, 0.08, 0.5 - i * 0.06), 0.05 + i * 0.055)
    return out


def sfx_splash():                     # a big gulp: deeper splash with a rising chime
    out = np.zeros(int(0.7 * SR))
    x = noise_burst(0.45, 0.12)
    t = np.arange(len(x)) / SR
    mix_at(out, 1.3 * x * np.exp(-t * 6), 0.0)
    for i, f in enumerate((300, 380, 460, 560, 680, 820)):
        mix_at(out, bubble(f, 0.09, 0.45), 0.03 + i * 0.04)
    for i, m in enumerate((79, 83, 86)):
        mix_at(out, bell(m, 0.3, 0.3), 0.18 + i * 0.06)
    return out


def sfx_combo():                      # a colour disappeared from the board: sparkly arpeggio
    out = np.zeros(int(0.8 * SR))
    for i, m in enumerate((84, 88, 91, 96, 100)):
        mix_at(out, bell(m, 0.35, 0.42), i * 0.05)
    t = t_axis(0.5)
    mix_at(out, 0.1 * sweep(1200, 3200, t) * env(len(t), a=0.05, d=0.2, r=0.1), 0.05)
    return out


def sfx_warning():                    # few moves left: two short soft alarm blips
    out = np.zeros(int(0.42 * SR))
    for i in range(2):
        t = t_axis(0.12)
        x = (tri(880, t) + 0.4 * sine(1320, t)) * env(len(t), a=0.004, d=0.06, s=0.3, r=0.03)
        mix_at(out, 0.5 * x, i * 0.18)
    return out


def sfx_denied():                     # that colour is already yours
    t = t_axis(0.2)
    x = soft_square(150, t, 4) * env(len(t), a=0.005, d=0.1, s=0.3, r=0.05)
    return 0.5 * x


def sfx_start():                      # new board: icy chime going up
    out = np.zeros(int(0.7 * SR))
    for i, m in enumerate((72, 76, 79, 84)):
        mix_at(out, bell(m, 0.38, 0.4), i * 0.07)
    return out


def sfx_unlock():                     # next level unlocked
    out = np.zeros(int(0.9 * SR))
    mix_at(out, bell(79, 0.3, 0.4), 0.0)
    mix_at(out, bell(86, 0.6, 0.45), 0.12)
    mix_at(out, bell(91, 0.7, 0.3), 0.24)
    return out


def sfx_victory():                    # level complete fanfare
    out = np.zeros(int(2.4 * SR))
    notes = [(65, 0.0, 0.12), (69, 0.11, 0.12), (72, 0.22, 0.12), (77, 0.33, 0.28),
             (76, 0.6, 0.11), (77, 0.71, 0.11), (81, 0.82, 1.0)]
    for m, st, dd in notes:
        mix_at(out, lead(m, dd + 0.1, 0.5), st)
        mix_at(out, bell(m + 12, dd + 0.3, 0.25), st)
    mix_at(out, pad([53, 57, 60, 65], 1.5, 0.35), 0.82)
    for st, m in ((0.0, 41), (0.33, 48), (0.82, 41)):
        mix_at(out, bass(m, 0.45, 0.5), st)
        mix_at(out, kick(0.5), st)
    for i in range(14):
        mix_at(out, bubble(500 + 90 * int(rng.integers(0, 8)), 0.08, 0.2), 0.9 + i * 0.07)
    return out


def sfx_defeat():                     # out of moves: sad trombone-ish slide + bloop
    out = np.zeros(int(2.0 * SR))
    for i, m in enumerate((67, 66, 65)):
        mix_at(out, lead(m, 0.32, 0.5), i * 0.34)
    t = t_axis(0.9)
    f = hz(64) * (1 - 0.07 * t / t[-1]) * (1 + 0.03 * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * env(len(t), a=0.02, d=0.6, s=0.4, r=0.2)
    mix_at(out, 0.5 * x, 1.02)
    mix_at(out, bass(40, 0.9, 0.35), 1.02)
    mix_at(out, bubble(220, 0.2, 0.4), 1.8)
    return out


SFX_LEVEL = {"hover": 0.22, "click": 0.4, "flood": 0.5, "splash": 0.65, "combo": 0.55, "warning": 0.5,
             "denied": 0.45, "start": 0.45, "unlock": 0.55, "victory": 0.8, "defeat": 0.75}
SFX = {"click": sfx_click, "hover": sfx_hover, "flood": sfx_flood, "splash": sfx_splash, "combo": sfx_combo,
       "warning": sfx_warning, "denied": sfx_denied, "start": sfx_start, "unlock": sfx_unlock,
       "victory": sfx_victory, "defeat": sfx_defeat}


# ------------------------------------------------------------------- music
CHORD_TONES = {  # chord name -> (root midi in octave 3, triad intervals)
    "C": (48, (0, 4, 7)), "Am": (45, (0, 3, 7)), "F": (41, (0, 4, 7)), "G": (43, (0, 4, 7)),
    "Dm": (50, (0, 3, 7)), "Em": (52, (0, 3, 7)), "Bb": (46, (0, 4, 7)), "Gm": (43, (0, 3, 7)),
    "D": (50, (0, 4, 7)), "A": (45, (0, 4, 7)), "Bm": (47, (0, 3, 7)),
}


def chord_notes(name, octave_shift=0):
    root, iv = CHORD_TONES[name]
    return [root + 12 * octave_shift + i for i in iv]


def render_loop(bars, bpm, render_bar, echo=0.22):
    beat = 60.0 / bpm
    bar_len = 4 * beat
    total = bars * bar_len
    n = int(round(total * SR))
    buf = np.zeros(n + int(4 * SR))
    for b in range(bars):
        render_bar(buf, b, b * bar_len, beat)
    d = int(0.75 * beat * SR)
    wet = np.zeros_like(buf)
    wet[d:] += buf[:-d] * echo
    wet[2 * d:] += buf[:-2 * d] * echo * echo
    buf = buf + wet
    loop = buf[:n].copy()
    tail = buf[n:]
    k = min(len(tail), n)
    loop[:k] += tail[:k]
    return normalize(loop, 0.8)


def make_melody(chords, bars, scale, seed, rest_bars=(), start=74):
    g = np.random.default_rng(seed)
    mel, cur = [], start
    for b in range(bars):
        tones = {(n % 12) for n in chord_notes(chords[b % len(chords)])}
        if b in rest_bars:
            mel.append([(None, 8)])
            continue
        pattern = [[2, 1, 1, 2, 2], [3, 1, 4], [2, 2, 2, 2], [1, 1, 2, 4], [4, 2, 2], [2, 1, 1, 4]][g.integers(0, 6)]
        if b % 4 == 3:
            pattern = [2, 2, 4]
        notes = []
        for i, length in enumerate(pattern):
            cands = [n for n in scale if abs(n - cur) <= 5 and n != cur] or scale
            if i == 0 or length >= 4:
                cands = [n for n in cands if n % 12 in tones] or cands
            cur = int(g.choice(cands))
            notes.append((cur, length))
        if b % 8 == 7:
            notes[-1] = (None, notes[-1][1])
        mel.append(notes)
    return mel


# "Színes áradat" – menu theme, F major, bouncy and splashy
MENU_CHORDS = ["F", "Dm", "Bb", "C", "F", "Am", "Bb", "C", "Dm", "Bb", "F", "C", "Bb", "C", "F", "C"]
MENU_MELODY = make_melody(MENU_CHORDS, 16, [65, 67, 69, 70, 72, 74, 76, 77, 79, 81], seed=31, start=72)


def menu_bar(buf, b, start, beat):
    tones = chord_notes(MENU_CHORDS[b])
    e = beat / 2
    for i, m in enumerate((tones[0], tones[0] + 12, tones[0] + 7, tones[0] + 12)):
        mix_at(buf, bass(m - 12 if m > 52 else m, beat * 0.85, 0.5), start + i * beat)
    arp = [tones[0] + 24, tones[1] + 24, tones[2] + 24, tones[1] + 24 + 12 * (b % 2)] * 2
    for i, m in enumerate(arp):
        mix_at(buf, pluck(m, e * 1.5, 0.2 if i % 2 else 0.26), start + i * e)
    pos = 0
    for m, length in MENU_MELODY[b]:
        if m is not None:
            mix_at(buf, lead(m, length * e * 0.95, 0.3), start + pos * e)
            mix_at(buf, bell(m + 12, length * e, 0.08), start + pos * e)
        pos += length
    for i in range(4):
        mix_at(buf, kick(0.33 if i % 2 == 0 else 0.18), start + i * beat)
        mix_at(buf, shaker(0.08), start + i * beat + e)
    if b % 2 == 1:
        mix_at(buf, bubble(600 + 80 * (b % 4), 0.08, 0.12), start + 3.5 * beat)


# "Hullámzó jégtáblák" – gameplay loop, G major / E minor, calm and thoughtful
GAME_CHORDS = ["Em", "C", "G", "D", "Em", "Am", "C", "D", "G", "Em", "C", "D", "Am", "C", "G", "D"]
GAME_MELODY = make_melody(GAME_CHORDS, 32, [64, 66, 67, 69, 71, 72, 74, 76, 78, 79], seed=47,
                          rest_bars=(0, 1, 16, 17), start=71)


def game_bar(buf, b, start, beat):
    tones = chord_notes(GAME_CHORDS[b % len(GAME_CHORDS)])
    e = beat / 2
    mix_at(buf, pad([t + 12 for t in tones], 4 * beat + 0.3, 0.16), start)
    mix_at(buf, bass(tones[0], beat * 1.8, 0.42), start)
    mix_at(buf, bass(tones[0] + 7 if tones[0] + 7 < 56 else tones[0] - 5, beat * 1.8, 0.32), start + 2 * beat)
    patt = [0, 2, 1, 2, 0, 2, 1, 2] if b % 2 == 0 else [0, 1, 2, 1, 2, 1, 0, 1]
    for i, k in enumerate(patt):
        mix_at(buf, bell(tones[k] + 24, e * 1.7, 0.15 if i % 2 == 0 else 0.1), start + i * e)
    pos = 0
    for m, length in GAME_MELODY[b]:
        if m is not None:
            mix_at(buf, pluck(m, length * e * 1.2, 0.3), start + pos * e)
        pos += length
    for i in range(4):
        mix_at(buf, shaker(0.04 if i % 2 else 0.028), start + i * beat + e)
    if b % 2 == 1:
        mix_at(buf, kick(0.15), start)
    if b % 4 == 2:
        mix_at(buf, bubble(520, 0.09, 0.08), start + 2.5 * beat)
        mix_at(buf, bubble(660, 0.09, 0.07), start + 2.75 * beat)


# --------------------------------------------------------------------- io
def write_wav(path: Path, x: np.ndarray):
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def write_ogg(path: Path, x: np.ndarray, quality=3):
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "tmp.wav"
        write_wav(wav, x)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis",
                        "-q:a", str(quality), "-metadata", "title=" + path.stem,
                        "-metadata", "artist=TuxoFlood", "-metadata", "copyright=CC0 1.0", str(path)], check=True)


def main():
    (ROOT / "sounds").mkdir(parents=True, exist_ok=True)
    (ROOT / "music").mkdir(parents=True, exist_ok=True)
    for name, fn in SFX.items():
        x = fn()
        fade = min(len(x), int(0.01 * SR))
        x[-fade:] *= np.linspace(1, 0, fade)
        write_wav(ROOT / "sounds" / f"{name}.wav", normalize(x, SFX_LEVEL[name]))
    write_ogg(ROOT / "music" / "menu.ogg", render_loop(len(MENU_CHORDS), 116, menu_bar))
    write_ogg(ROOT / "music" / "game.ogg", render_loop(32, 88, game_bar, echo=0.3))
    print("sounds written to", ROOT)


if __name__ == "__main__":
    main()
