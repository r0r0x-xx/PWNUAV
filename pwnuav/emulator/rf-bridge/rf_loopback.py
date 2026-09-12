#!/usr/bin/env python3
"""Cabled/caged RF loopback: transmit a MAVLink frame on the HackRF and
recover it on the Pluto — integration scaffold for the GFSK bridge over real radios.

This script will NOT recover a frame as-is: the GFSK receiver has no preamble-based
timing recovery yet. It is scaffolding for the real-radio bring-up.

RUN ONLY inside a Faraday cage or cabled with attenuators. Requires SoapySDR
with SoapyHackRF and SoapyPlutoSDR.

Usage: python rf_loopback.py
"""
from __future__ import annotations

import time

import numpy as np
from pymavlink import mavutil

from pwnuav.rf.gfsk import FS
from pwnuav.rf.modem import decode, encode
from pwnuav.rf.soapy_io import HAVE_SOAPY, SdrSink, SdrSource


def main() -> None:
    if not HAVE_SOAPY:
        raise SystemExit("SoapySDR not installed; cannot drive radios.")
    mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    msg = mav.heartbeat_encode(
        mavutil.mavlink.MAV_TYPE_QUADROTOR,
        mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0,
        mavutil.mavlink.MAV_STATE_ACTIVE,
    )
    payload = msg.pack(mav)
    iq = encode(payload)
    pad = np.zeros(FS // 100, dtype=np.complex64)  # 10 ms guard
    burst = np.concatenate([pad, iq, pad])

    rx = SdrSource(freq=915e6, fs=FS)
    tx = SdrSink(freq=915e6, fs=FS)
    try:
        tx.send(burst)
        time.sleep(0.05)
        samples = rx.recv(len(burst) * 4)
    finally:
        tx.close()
        rx.close()

    frames = decode(samples)
    print(f"[+] recovered {len(frames)} frame(s)")
    for f in frames:
        print("    ", f == payload, f.hex())


if __name__ == "__main__":
    main()
