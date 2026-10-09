"""
Finalizzazione degli asset audio di WHAT IS BELOW: pulizia (continua, dissolvenze, silenzio in testa),
livello per categoria, limitatore, codifica Vorbis con ffmpeg, verifica sul file DECODIFICATO
(lunghezza esatta con due decoder, picco, continuità del punto di loop) e spettrogrammi di controllo.
"""
from __future__ import annotations

import json
import os
import subprocess

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw
from scipy import signal
from scipy.io import wavfile

from dsp import (SR, active_rms_db, circular, db_to_lin, fade, highpass, limiter, lin_to_db, mono, ns,
                 peak_db, rms_db)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'tools', 'audio', 'cache')
OUT = os.path.join(ROOT, 'public', 'assets', 'audio')
MANIFEST = os.path.join(OUT, 'manifest.json')

CEILING_DB = -1.3        # tetto prima della codifica (il file decodificato deve restare ≤ −1 dBFS)
DECODED_MAX_DB = -1.0
VORBIS_Q = 6


# ───────────────────────── pulizia e livello ─────────────────────────

def _trim_head(x: np.ndarray, thr_db: float = -50.0, keep: float = 0.001) -> np.ndarray:
    """Toglie il silenzio iniziale: l'attacco deve cominciare entro pochi ms."""
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=0)
    thr = np.max(a) * db_to_lin(thr_db)
    idx = int(np.argmax(a > thr))
    cut = max(0, idx - ns(keep))
    return x[..., cut:]


def rotate_loop(x: np.ndarray, max_shift: float | None) -> np.ndarray:
    """Sceglie il punto d'inizio di un loop (rotazione circolare: il loop non cambia) dove il segnale
    è quasi nullo e quieto. Il codificatore Vorbis vede il file come preceduto e seguito da silenzio:
    se ai bordi c'è un gradino, l'errore di codifica lascia un piccolo click alla giunzione.
    max_shift: rotazione massima (s) all'indietro rispetto all'inizio nominale; None = libera."""
    x2 = x if x.ndim == 2 else x[None]
    n = x2.shape[-1]
    r = np.sqrt(np.mean(x2 ** 2)) + 1e-12
    from scipy.ndimage import uniform_filter1d
    local = np.sqrt(uniform_filter1d(np.mean(x2 ** 2, axis=0), ns(0.004), mode='wrap'))
    edge = np.sum(np.abs(x2) + np.abs(np.roll(x2, 1, axis=-1)), axis=0)
    score = edge / r + 2.0 * local / r
    if max_shift is not None:
        allowed = np.zeros(n, dtype=bool)
        allowed[0] = True
        allowed[n - ns(max_shift):] = True
        score = np.where(allowed, score, np.inf)
    s = int(np.argmin(score))
    return np.roll(x, -s, axis=-1)


def finalize(x: np.ndarray, spec) -> np.ndarray:
    """Porta un segnale grezzo allo stato finale (prima della codifica)."""
    x = np.asarray(x, dtype=np.float64)
    want_ch = spec.channels
    if want_ch == 2 and x.ndim == 1:
        x = np.stack([x, x])
    if want_ch == 1 and x.ndim == 2:
        x = x.mean(axis=0)
    n = spec.n
    if spec.loop:
        if x.shape[-1] != n:
            raise ValueError(f'{spec.id}: un loop deve avere esattamente {n} campioni (ne ha {x.shape[-1]})')
        # niente continua: media nulla e passa-alto in regime circolare (il loop resta continuo)
        x = x - x.mean(axis=-1, keepdims=True)
        x = circular(lambda s: highpass(s, 12.0, 2), x, pad=2.0)
    else:
        x = _trim_head(x)
        x = highpass(x, 12.0, 2)
        if x.shape[-1] < n:
            x = np.concatenate([x, np.zeros(x.shape[:-1] + (n - x.shape[-1],))], axis=-1)
        x = x[..., :n]
        fout = float(np.clip(0.12 * spec.dur, 0.006, 0.08))
        x = fade(x, 0.0008, fout)
    # livello: RMS "attivo" verso l'obiettivo, poi limitatore con riduzione massima limitata
    level = active_rms_db(x)
    g = db_to_lin(spec.rms - level)
    y = x * g
    pk = peak_db(y)
    if pk > CEILING_DB + spec.max_gr:
        y *= db_to_lin(CEILING_DB + spec.max_gr - pk)
    y = limiter(y, CEILING_DB, lookahead=0.004, release=spec.release, circular=spec.loop)
    if spec.loop:
        y = rotate_loop(y, spec.params.get('rotate_max'))
    return y


# ───────────────────────── codifica e verifica ─────────────────────────

def _write_wav(path: str, x: np.ndarray) -> None:
    data = x.T if x.ndim == 2 else x
    wavfile.write(path, SR, np.ascontiguousarray(data, dtype=np.float32))


def _encode(wav: str, ogg: str, n: int) -> None:
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', wav, '-c:a', 'libvorbis', '-q:a', str(VORBIS_Q),
           '-ar', str(SR), '-fflags', '+bitexact', '-flags:a', '+bitexact', '-map_metadata', '-1']
    if n < 2 * SR:
        # pagine Ogg piccole: con i file brevi il decoder di ffmpeg (quello di Chromium/Electron)
        # altrimenti sbaglia il taglio finale di qualche decina di campioni (verificato)
        cmd += ['-page_duration', '20000']
    subprocess.run(cmd + [ogg], check=True)


def decode_libvorbis(path: str) -> np.ndarray:
    y, sr = sf.read(path, dtype='float32', always_2d=True)
    assert sr == SR
    return y.T.astype(np.float64)


def decode_ffmpeg(path: str, ch: int) -> np.ndarray:
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-acodec', 'pcm_f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).reshape(-1, ch).T.astype(np.float64)


def loop_seam(x: np.ndarray) -> dict:
    """Continuità del punto di loop: confronta il salto fine→inizio con i salti tipici del file
    e l'energia della derivata seconda attorno alla giunzione con quella di tutte le altre posizioni."""
    x = x if x.ndim == 2 else x[None]
    n = x.shape[-1]
    d = np.diff(x, axis=-1)
    typ = np.sqrt(np.mean(d ** 2, axis=-1)) + 1e-12
    jump = np.abs(x[:, 0] - x[:, -1])
    jump_ratio = float(np.max(jump / typ))
    # "click" alla giunzione: picco del segnale passato in un passa-alto a 3 kHz attorno alla giunzione
    # (fine → inizio), confrontato con la stessa misura in 200 punti interni presi a caso
    L = min(ns(0.05), n // 2)
    w = ns(0.0015)

    def click(z):
        h = highpass(z, 3000.0, 4)
        return float(np.max(np.abs(h[:, L - w:L + 2 * w])))

    seam = click(np.concatenate([x[:, n - L:], x[:, :L]], axis=-1))
    rng = np.random.default_rng(0)
    ref = np.array([click(x[:, p - L:p + L]) for p in rng.integers(L, n - L, 200)])
    return {'jump_ratio': jump_ratio,
            'seam_pct': float(np.mean(ref < seam) * 100.0),
            'seam_click_db': float(lin_to_db(seam)),
            'ref_click_db': float(lin_to_db(np.median(ref)))}


def encode_and_verify(y: np.ndarray, spec, keep_wav: bool = False) -> dict:
    """Codifica in Ogg Vorbis e verifica il risultato decodificato; riduce il guadagno se la codifica
    supera il tetto di picco. Restituisce le metriche misurate sul file finale."""
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(CACHE, f'{spec.id}.wav')
    ogg = os.path.join(OUT, f'{spec.id}.ogg')
    n = y.shape[-1]
    ch = 1 if y.ndim == 1 else y.shape[0]
    for _attempt in range(5):
        _write_wav(wav, y)
        _encode(wav, ogg, n)
        dec = decode_libvorbis(ogg)
        pk = peak_db(dec)
        if pk <= DECODED_MAX_DB - 0.05:
            break
        y = y * db_to_lin(DECODED_MAX_DB - 0.15 - pk)
    dec_ff = decode_ffmpeg(ogg, ch)
    if dec.shape[-1] != n or dec_ff.shape[-1] != n:
        raise RuntimeError(f'{spec.id}: lunghezza decodificata errata (libvorbis {dec.shape[-1]}, '
                           f'ffmpeg {dec_ff.shape[-1]}, attesa {n})')
    if dec.shape[0] != spec.channels:
        raise RuntimeError(f'{spec.id}: canali {dec.shape[0]} invece di {spec.channels}')
    if not keep_wav:
        os.remove(wav)
    a = np.abs(dec) if dec.ndim == 1 else np.max(np.abs(dec), axis=0)
    head = int(np.argmax(a > np.max(a) * db_to_lin(-40)))
    res = {
        'id': spec.id,
        'samples': n,
        'duration': n / SR,
        'channels': ch,
        'peak_db': peak_db(dec),
        'rms_db': rms_db(dec),
        'active_rms_db': active_rms_db(dec),
        'dc': float(np.max(np.abs(dec.mean(axis=-1)))),
        'head_ms': head / SR * 1000.0,
        'bytes': os.path.getsize(ogg),
    }
    if spec.loop:
        res.update(loop_seam(dec))
    return res, dec


# ───────────────────────── manifest ─────────────────────────

def manifest_entry(spec) -> dict:
    return {
        'file': f'{spec.id}.ogg',
        'duration': round(spec.n / SR, 4),
        'loop': bool(spec.loop),
        'channels': int(spec.channels),
        'gain': round(float(spec.gain), 3),
        'category': spec.category,
    }


def write_manifest(entries: dict, replace: bool) -> None:
    data = {}
    if not replace and os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8') as fh:
            data = json.load(fh)
    data.update(entries)
    data = {k: data[k] for k in sorted(data)}
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


# ───────────────────────── spettrogrammi di controllo ─────────────────────────

_CMAP_PTS = np.array([
    [0.00, 0, 0, 4], [0.15, 31, 12, 72], [0.30, 85, 15, 109], [0.45, 136, 34, 106],
    [0.60, 186, 54, 85], [0.72, 227, 89, 51], [0.84, 249, 140, 10], [0.93, 249, 201, 50], [1.00, 252, 255, 164]])


def _cmap(v: np.ndarray) -> np.ndarray:
    out = np.empty(v.shape + (3,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(v, _CMAP_PTS[:, 0], _CMAP_PTS[:, c + 1]).astype(np.uint8)
    return out


def spectrogram_png(x: np.ndarray, path: str, title: str = '', fmin: float = 30.0, fmax: float = 16000.0,
                    log_f: bool = True, height: int = 420, max_width: int = 1600, dyn_db: float = 85.0) -> None:
    """Spettrogramma (asse delle frequenze logaritmico) + forma d'onda, salvato in PNG."""
    m = mono(x)
    dur = len(m) / SR
    nfft = 4096 if log_f else 2048
    hop = max(64, int(np.ceil(len(m) / max_width)))
    hop = min(hop, nfft // 2)
    win = signal.get_window('hann', nfft)
    pad = np.concatenate([np.zeros(nfft // 2), m, np.zeros(nfft)])
    frames = 1 + (len(pad) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(frames)[:, None]
    S = np.abs(np.fft.rfft(pad[idx] * win, axis=1)).T          # (bins, frames)
    S = 20 * np.log10(S + 1e-9)
    S -= S.max()
    freqs = np.fft.rfftfreq(nfft, 1.0 / SR)
    rows = np.arange(height)
    if log_f:
        fr = fmin * (fmax / fmin) ** (1 - rows / (height - 1))
    else:
        fr = fmax * (1 - rows / (height - 1))
    img = np.empty((height, S.shape[1]))
    for j in range(S.shape[1]):
        img[:, j] = np.interp(fr, freqs, S[:, j])
    v = np.clip((img + dyn_db) / dyn_db, 0, 1)
    rgb = _cmap(v)
    wav_h = 90
    W = rgb.shape[1]
    canvas = Image.new('RGB', (W + 60, height + wav_h + 30), (12, 12, 16))
    canvas.paste(Image.fromarray(rgb), (60, 20))
    d = ImageDraw.Draw(canvas)
    d.text((62, 3), f'{title}  ({dur:.2f} s)', fill=(230, 230, 230))
    ticks = [50, 100, 200, 500, 1000, 2000, 5000, 10000] if log_f else list(range(0, int(fmax) + 1, 2000))
    for f in ticks:
        if not (fmin <= f <= fmax):
            continue
        y = (1 - np.log(f / fmin) / np.log(fmax / fmin)) * (height - 1) if log_f else (1 - f / fmax) * (height - 1)
        y = int(round(y)) + 20
        d.line([(55, y), (60 + W, y)], fill=(70, 70, 80))
        d.text((2, y - 6), f'{f / 1000:g}k' if f >= 1000 else f'{f}', fill=(200, 200, 200))
    # secondi
    for s in np.arange(0, dur + 1e-9, 0.5 if dur <= 4 else (2.0 if dur <= 20 else 8.0)):
        xx = 60 + int(s / dur * (W - 1))
        d.line([(xx, height + 20), (xx, height + 26)], fill=(200, 200, 200))
        d.text((xx + 2, height + 14 + wav_h), f'{s:g}s', fill=(200, 200, 200))
    # forma d'onda (min/max per colonna) con righe a -6 e -20 dB
    y0 = height + 25 + wav_h // 2
    cols = np.array_split(m, W)
    for j, c in enumerate(cols):
        if len(c) == 0:
            continue
        lo, hi = float(c.min()), float(c.max())
        d.line([(60 + j, y0 - int(hi * wav_h / 2)), (60 + j, y0 - int(lo * wav_h / 2))], fill=(120, 200, 255))
    for lvl in (0.5, 0.1):
        for sgn in (1, -1):
            yy = y0 - int(sgn * lvl * wav_h / 2)
            d.line([(60, yy), (60 + W, yy)], fill=(60, 60, 70))
    canvas.save(path)
