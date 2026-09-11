"""Software channel impairments for testing the RF receiver.

Lets the receiver be validated against realistic effects (leading noise,
carrier frequency offset, AWGN) without any radio.
"""
from __future__ import annotations

import numpy as np

from pwnuav.rf.gfsk import FS


def prepend_noise(iq: np.ndarray, nsamples: int, rng: np.random.Generator,
                  amp: float | None = None) -> np.ndarray:
    if amp is None:
        amp = float(np.sqrt(np.mean(np.abs(iq) ** 2)))
    noise = (amp / np.sqrt(2)) * (
        rng.standard_normal(nsamples) + 1j * rng.standard_normal(nsamples))
    return np.concatenate([noise.astype(np.complex64), np.asarray(iq)])


def apply_cfo(iq: np.ndarray, f0: float, fs: float = FS) -> np.ndarray:
    n = np.arange(len(iq))
    return (np.asarray(iq) * np.exp(1j * 2 * np.pi * f0 / fs * n)).astype(np.complex64)


def add_awgn(iq: np.ndarray, snr_db: float,
             rng: np.random.Generator) -> np.ndarray:
    iq = np.asarray(iq)
    power = np.mean(np.abs(iq) ** 2)
    sigma = np.sqrt(power / (2 * 10 ** (snr_db / 10)))
    noise = sigma * (rng.standard_normal(len(iq)) + 1j * rng.standard_normal(len(iq)))
    return (iq + noise).astype(np.complex64)
