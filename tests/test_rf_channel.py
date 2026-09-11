import numpy as np

from pwnuav.rf.channel import prepend_noise, apply_cfo, add_awgn


def test_prepend_noise_extends_and_preserves_tail():
    rng = np.random.default_rng(0)
    iq = np.ones(100, dtype=np.complex64)
    out = prepend_noise(iq, nsamples=40, rng=rng)
    assert len(out) == 140
    assert np.allclose(out[40:], iq)


def test_apply_cfo_shifts_spectrum_peak():
    fs = 1_000_000
    n = np.arange(4096)
    tone = np.exp(1j * 2 * np.pi * 0.0 / fs * n).astype(np.complex64)  # DC tone
    shifted = apply_cfo(tone, f0=50_000, fs=fs)
    freqs = np.fft.fftfreq(len(shifted), d=1 / fs)
    peak = freqs[np.argmax(np.abs(np.fft.fft(shifted)))]
    assert abs(peak - 50_000) < 1_000


def test_add_awgn_hits_target_snr():
    rng = np.random.default_rng(1)
    iq = np.exp(1j * np.linspace(0, 100, 20000)).astype(np.complex64)
    noisy = add_awgn(iq, snr_db=10, rng=rng)
    noise = noisy - iq
    snr = 10 * np.log10(np.mean(np.abs(iq) ** 2) / np.mean(np.abs(noise) ** 2))
    assert abs(snr - 10) < 1.0
