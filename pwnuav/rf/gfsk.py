"""Minimal GFSK modem on complex baseband (numpy only).

Deterministic loopback design: Gaussian-shaped NRZ frequency modulation,
recovered with a differential (quadrature) discriminator and per-symbol
integrate-and-dump. Simplified relative to a real SiK radio (no FHSS, no FEC,
no closed-loop timing recovery) — enough to carry MAVLink over an IQ stream
and to demonstrate demodulation (PWNUAV PA-01).

NOTE: demodulate() assumes frame-aligned IQ (software loopback). Recovering frames
off a real radio additionally needs preamble-correlation timing recovery and CFO/DC removal.
"""
from __future__ import annotations

import numpy as np

FS = 1_000_000       # sample rate (Hz)
BAUD = 100_000       # symbol rate (bps)
SPS = FS // BAUD     # samples per symbol (10)
DEV = 25_000         # frequency deviation (Hz); mod index h = 2*DEV/BAUD = 0.5
BT = 0.5             # Gaussian bandwidth-time product


def bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))  # MSB-first


def bits_to_bytes(bits: np.ndarray) -> bytes:
    n = (len(bits) // 8) * 8
    return np.packbits(bits[:n].astype(np.uint8)).tobytes()


def _gaussian_taps(sps: int, span: int = 4, bt: float = BT) -> np.ndarray:
    ntaps = sps * span
    if ntaps % 2 == 0:
        ntaps += 1
    t = (np.arange(ntaps) - (ntaps - 1) / 2) / sps  # in symbol units
    sigma = np.sqrt(np.log(2)) / (2 * np.pi * bt)
    h = np.exp(-(t ** 2) / (2 * sigma ** 2))
    return h / h.sum()


def modulate(bits: np.ndarray, sps: int = SPS, fs: float = FS,
             dev: float = DEV, bt: float = BT) -> np.ndarray:
    symbols = 2.0 * bits.astype(np.float64) - 1.0        # {0,1} -> {-1,+1}
    nrz = np.repeat(symbols, sps)
    shaped = np.convolve(nrz, _gaussian_taps(sps, 4, bt), mode="same")
    phase = 2 * np.pi * dev / fs * np.cumsum(shaped)
    return np.exp(1j * phase).astype(np.complex64)


def demodulate(iq: np.ndarray, nbits: int, sps: int = SPS) -> np.ndarray:
    x = np.asarray(iq)
    inst = np.angle(x[1:] * np.conj(x[:-1]))
    inst = np.concatenate(([inst[0] if len(inst) else 0.0], inst))
    bits = np.empty(nbits, dtype=np.uint8)
    for k in range(nbits):
        window = inst[k * sps:(k + 1) * sps]
        bits[k] = 1 if window.sum() > 0 else 0
    return bits
