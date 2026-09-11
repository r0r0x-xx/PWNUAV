#!/usr/bin/env python3
"""PoC 01 - MAVLink Recon (Terminal 2 — attacker).

Requires the drone running in Terminal 1 (`python attacks/demos/drone.py`).
Discovers the drone by listening alone: fingerprint, enumeration and message inventory.
Over-the-air version: attacks/01-recon/recon_aire.py
"""
import argparse
import os
os.environ.setdefault("MAVLINK20", "1")
from pwnuav.tui import ClientLink, Activity, hw_check, Steps, run_dashboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    link = ClientLink(a.connect); act = Activity(); hw = hw_check()
    act.log("hardware checked — passive listening on the link")

    def s1(): act.log("[RC-01] listening without authenticating...")
    def s2(): act.log("[RC-02] link fingerprint: MAVLink2 (0xFD) + CRC-16")
    def s3():
        hb = link.last.get("HEARTBEAT")
        if hb:
            act.log(f"[RC-03] HEARTBEAT: sysid={hb.get_srcSystem()} QUADROTOR / ARDUPILOTMEGA")
    def s4(): act.log("[PA-02] MAVLink message inventory by count")
    def s5():
        hb = link.last.get("HEARTBEAT")
        try: inc = hb.get_header().incompat_flags
        except Exception: inc = 0
        act.log(f"[+] evidence: incompat_flags=0x{inc:02X} (unsigned), no challenge/handshake")

    steps = Steps([(0.5, s1), (1.3, s2), (2.1, s3), (2.9, s4), (3.7, s5)])

    def extra():
        hb = link.last.get("HEARTBEAT")
        rows = []
        if hb:
            rows.append(f"sysid={hb.get_srcSystem()}  compid={hb.get_srcComponent()}  "
                        f"QUADROTOR / ARDUPILOTMEGA")
            try: inc = hb.get_header().incompat_flags
            except Exception: inc = 0
            rows.append(f"MAVLink2 STX=0xFD  incompat_flags=0x{inc:02X} -> "
                        f"{'UNSIGNED (no one authenticated)' if inc == 0 else 'signed'}")
            try:
                raw = bytes(hb.get_msgbuf())
                rows.append("HEARTBEAT frame captured: " + raw[:16].hex(" ").upper())
            except Exception:
                pass
        inv = ", ".join(f"{k} x{v}" for k, v in sorted(link.counts.items()))
        rows.append("count: " + (inv or "scanning..."))
        return ("RECON — EVIDENCE", rows)

    run_dashboard("PoC 01 — MAVLink Recon", hw, link, act, steps,
                  total=a.seconds, plain=a.plain, extra_fn=extra)
    link.close()


if __name__ == "__main__":
    main()
