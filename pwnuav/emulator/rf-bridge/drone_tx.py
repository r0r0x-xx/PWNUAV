#!/usr/bin/env python3
"""Drone side: reads MAVLink from the emulator (UDP) and transmits it on the HackRF (915 MHz).

Bridge for running the PoCs over the air: the HackRF is the drone's radio. Faraday
cage ONLY. Requires SoapySDR + SoapyHackRF.
"""
from __future__ import annotations

import argparse

from pymavlink import mavutil

from pwnuav.rf.gfsk import FS
from pwnuav.rf.soapy_io import HAVE_SOAPY, SdrSink
from pwnuav.rf.transport import message_to_iq


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV drone TX bridge (HackRF)")
    ap.add_argument("--connect", default="udpin:127.0.0.1:14550")
    ap.add_argument("--freq", type=float, default=915e6)
    args = ap.parse_args()
    if not HAVE_SOAPY:
        raise SystemExit("SoapySDR not installed; cannot transmit.")
    mav = mavutil.mavlink_connection(args.connect)
    tx = SdrSink(freq=args.freq, fs=FS, driver="hackrf")
    print(f"[*] drone->HackRF bridge at {args.freq/1e6:.3f} MHz (CAGE ONLY)")
    try:
        while True:
            msg = mav.recv_match(blocking=True, timeout=1.0)
            if msg is None or msg.get_type() == "BAD_DATA":
                continue
            tx.send(message_to_iq(mav.mav, msg))
    finally:
        tx.close()


if __name__ == "__main__":
    main()
