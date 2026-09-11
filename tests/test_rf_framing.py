import pytest

from pwnuav.rf.framing import build_frame, find_frames, crc16_ccitt, SYNC


def test_crc16_ccitt_known_vector():
    # CRC-16/CCITT-FALSE of b"123456789" is 0x29B1
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_build_and_find_roundtrip():
    payload = b"hello mavlink"
    frame = build_frame(payload)
    assert find_frames(frame) == [payload]


def test_find_frames_amid_noise():
    payload = b"\x01\x02\x03\x04"
    stream = b"\x00\xff\x13" + build_frame(payload) + b"\x99\x99"
    assert find_frames(stream) == [payload]


def test_find_frames_rejects_corrupted_crc():
    payload = b"payload"
    frame = bytearray(build_frame(payload))
    frame[-1] ^= 0xFF  # corrupt CRC
    assert find_frames(bytes(frame)) == []


def test_build_frame_rejects_oversize_payload():
    with pytest.raises(ValueError):
        build_frame(b"x" * 256)
