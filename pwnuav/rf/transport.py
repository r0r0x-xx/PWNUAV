"""Carry MAVLink messages over the GFSK RF layer, end to end.

The drone side serializes a MAVLink message and modulates it (message_to_iq);
the attacker side recovers frames with the timing-recovering receiver and
parses them back to MAVLink (iq_to_messages). This is the byte/message-level
bridge the PoCs use on real radios: recon/eavesdrop parse received messages,
injection transmits a modulated command. Loopback-testable over the software
channel with no hardware.
"""
from __future__ import annotations

import numpy as np

from pwnuav.rf.modem import encode
from pwnuav.rf.receiver import receive


def message_to_iq(mav, msg) -> np.ndarray:
    return encode(msg.pack(mav))


def iq_to_messages(mav, iq: np.ndarray) -> list:
    out = []
    for frame in receive(iq):
        try:
            parsed = mav.decode(bytearray(frame))
        except Exception:
            continue
        if parsed is not None:
            out.append(parsed)
    return out
