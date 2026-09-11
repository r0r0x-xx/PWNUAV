import numpy as np

from pwnuav.rf.gfsk import (
    bytes_to_bits, bits_to_bytes, modulate, demodulate, SPS,
)


def test_bytes_bits_roundtrip():
    data = b"\x00\xff\xa5\x3c"
    bits = bytes_to_bits(data)
    assert bits.tolist() == [0, 0, 0, 0, 0, 0, 0, 0,
                             1, 1, 1, 1, 1, 1, 1, 1,
                             1, 0, 1, 0, 0, 1, 0, 1,
                             0, 0, 1, 1, 1, 1, 0, 0]
    assert bits_to_bytes(bits) == data


def test_gfsk_loopback_recovers_random_bits():
    rng = np.random.default_rng(1234)
    bits = rng.integers(0, 2, size=800, dtype=np.uint8)
    iq = modulate(bits)
    assert iq.dtype == np.complex64
    assert len(iq) == len(bits) * SPS
    out = demodulate(iq, nbits=len(bits))
    assert np.array_equal(out, bits)


def test_gfsk_loopback_survives_high_snr_noise():
    rng = np.random.default_rng(7)
    bits = rng.integers(0, 2, size=400, dtype=np.uint8)
    iq = modulate(bits)
    # add complex AWGN at ~20 dB SNR
    power = np.mean(np.abs(iq) ** 2)
    sigma = np.sqrt(power / (2 * 100))  # 20 dB
    noise = sigma * (rng.standard_normal(len(iq)) + 1j * rng.standard_normal(len(iq)))
    out = demodulate((iq + noise).astype(np.complex64), nbits=len(bits))
    ber = np.mean(out != bits)
    assert ber < 0.01
