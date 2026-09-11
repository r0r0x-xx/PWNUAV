"""PoC 01 - Recon MAVLink (PWNUAV RC-01/02/03, PA-02).

Passively discovers the vehicle: heartbeat, autopilot type, and the set of
MAVLink message IDs observed on the link.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field

from pwnuav.link import announce, connect


@dataclass
class ReconResult:
    heard: bool = False
    system_id: int | None = None
    component_id: int | None = None
    vehicle_type: int | None = None
    autopilot: int | None = None
    message_ids: set = field(default_factory=set)


def run_recon(conn_str: str, duration: float = 3.0) -> ReconResult:
    master = connect(conn_str)
    announce(master)
    result = ReconResult()
    deadline = time.time() + duration
    while time.time() < deadline:
        msg = master.recv_match(blocking=True, timeout=0.5)
        if msg is None:
            continue
        result.message_ids.add(msg.get_msgId())
        if msg.get_type() == "HEARTBEAT":
            result.heard = True
            result.system_id = msg.get_srcSystem()
            result.component_id = msg.get_srcComponent()
            result.vehicle_type = msg.type
            result.autopilot = msg.autopilot
    master.close()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV PoC 01 - Recon MAVLink")
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550",
                    help="mavutil connection string of the link to scan")
    ap.add_argument("--duration", type=float, default=3.0)
    args = ap.parse_args()
    r = run_recon(args.connect, args.duration)
    if not r.heard:
        print("[-] No HEARTBEAT observed; is the vehicle transmitting?")
        return
    print(f"[+] Vehicle found: sysid={r.system_id} compid={r.component_id}")
    print(f"    type={r.vehicle_type} autopilot={r.autopilot}")
    print(f"    message IDs seen: {sorted(r.message_ids)}")


if __name__ == "__main__":
    main()
