"""Link framing for the PWNUAV GFSK bridge.

Frame = PREAMBLE + SYNC + length(1) + payload + CRC16(2, big-endian).
CRC is CRC-16/CCITT-FALSE over (length byte + payload). Intentionally simple:
no FHSS, no FEC — this is a vulnerable-by-design lab link.
"""
from __future__ import annotations

PREAMBLE = b"\x55" * 8
SYNC = b"\x2d\xd4"


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def build_frame(payload: bytes) -> bytes:
    if len(payload) > 255:
        raise ValueError("payload too large for single frame (max 255 bytes)")
    body = bytes([len(payload)]) + payload
    crc = crc16_ccitt(body)
    return PREAMBLE + SYNC + body + bytes([(crc >> 8) & 0xFF, crc & 0xFF])


def find_frames(data: bytes) -> list[bytes]:
    """Scan a byte stream for valid frames; return the recovered payloads."""
    frames: list[bytes] = []
    n = len(data)
    i = 0
    while True:
        j = data.find(SYNC, i)
        if j < 0:
            break
        k = j + len(SYNC)          # index of length byte
        if k >= n:
            break
        length = data[k]
        body_end = k + 1 + length  # end of (length byte + payload)
        crc_end = body_end + 2
        if crc_end > n:
            i = j + 1
            continue
        body = data[k:body_end]
        crc_rx = (data[body_end] << 8) | data[body_end + 1]
        if crc16_ccitt(body) == crc_rx:
            frames.append(data[k + 1:body_end])
            i = crc_end
        else:
            i = j + 1
    return frames
