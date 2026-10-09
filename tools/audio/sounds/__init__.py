"""
Registro dei suoni di WHAT IS BELOW. Ogni modulo tematico registra i propri id con @sound(...):
la funzione riceve (spec, rng) e restituisce il segnale grezzo (mono (n,) o stereo (2, n));
livello, pulizia, codifica e verifica li fa master.py.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable

from dsp import SR

MODULES = ('ambience', 'world', 'fishing', 'voice', 'pappo', 'lulu', 'cucu', 'music', 'ui')


@dataclass
class Spec:
    id: str
    fn: Callable
    dur: float
    loop: bool = False
    channels: int = 1
    category: str = 'sfx'
    gain: float = 0.8          # guadagno consigliato al gioco (lineare)
    rms: float = -18.0         # obiettivo di RMS "attivo" (dBFS)
    max_gr: float = 4.0        # massima riduzione di picco affidata al limitatore (dB)
    release: float = 0.06      # rilascio del limitatore (s)
    params: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(round(self.dur * SR))


REGISTRY: dict[str, Spec] = {}


def register(sid: str, fn: Callable, dur: float, **kw) -> None:
    if sid in REGISTRY:
        raise ValueError(f'id duplicato: {sid}')
    REGISTRY[sid] = Spec(id=sid, fn=fn, dur=dur, **kw)


def sound(sid: str, dur: float, **kw):
    """Decoratore: registra un generatore di suono sotto l'id `sid`."""
    def deco(fn):
        register(sid, fn, dur, **kw)
        return fn
    return deco


def load_all() -> dict[str, Spec]:
    for m in MODULES:
        try:
            importlib.import_module(f'sounds.{m}')
        except ModuleNotFoundError as e:
            if e.name != f'sounds.{m}':
                raise
    return REGISTRY
