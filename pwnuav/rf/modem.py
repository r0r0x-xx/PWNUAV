"""Full software modem: MAVLink bytes <-> GFSK IQ, via the link framing.

encode() wraps a payload in a frame and modulates it; decode() demodulates an
IQ stream and returns every valid frame's payload. Loopback-testable end to
end with no hardware.

NOTE: decode() assumes frame-aligned IQ (software loopback). Recovering frames
off a real radio additionally needs preamble-correlation timing recovery.
"""
from __future__ import annotations

import numpy as np

from pwnuav.rf.framing import build_frame, find_frames
from pwnuav.rf.gfsk import SPS, bits_to_bytes, bytes_to_bits, demodulate, modulate


def encode(payload: bytes, sps: int = SPS) -> np.ndarray:
    bits = bytes_to_bits(build_frame(payload))
    return modulate(bits, sps=sps)


def decode(iq: np.ndarray, sps: int = SPS) -> list[bytes]:
    nbits = len(iq) // sps
    bits = demodulate(iq, nbits=nbits, sps=sps)
    return find_frames(bits_to_bytes(bits))
