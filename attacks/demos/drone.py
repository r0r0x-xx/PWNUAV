#!/usr/bin/env python3
"""Terminal 1 — DRONE EMULATOR (live telemetry console).

Hosts the vulnerable-by-design drone (MAVLink hub + DroneStub) and shows its
console: state (ASCII) + a realistic stream of MAVLink telemetry and events.
When Terminal 2 launches an attack, the telemetry reflects the change (armed,
position jump, downlink loss) — without labels, like a real console.

Usage: python attacks/demos/drone.py   (port 14550, venv: .venv-radio)
The attacks (Terminal 2) connect to  udpout:127.0.0.1:14550
"""
import argparse
import collections
import math
import os
import time
os.environ.setdefault("MAVLINK20", "1")
from pwnuav import demo
from pwnuav.drone_stub import DroneStub
from pwnuav.mav_hub import MavHub
from pwnuav.tui import ClientLink, hw_check, frame_drone, draw, hide_cursor, show_cursor


class BackendLog:
    """Realistic telemetry/event stream derived from the link (no editorializing)."""
    def __init__(self, client, n=12):
        self.c = client
        self.buf = collections.deque(maxlen=n)
        self.prev_armed = None
        self.prev_mode = None
        self.prev_pos = None
        self.prev_up = True
        self.t_tel = 0.0
        self.cyc = 0

    def log(self, m):
        self.buf.append((time.strftime("%H:%M:%S"), m))

    def tick(self):
        now = time.time()
        c = self.c; last = c.last
        hb = last.get("HEARTBEAT"); g = last.get("GLOBAL_POSITION_INT")
        ss = last.get("SYS_STATUS"); at = last.get("ATTITUDE")
        armed = c.armed(); up = c.link_up()

        if hb and self.prev_mode is not None and hb.custom_mode != self.prev_mode:
            if hb.custom_mode == 6:
                self.log("FAILSAFE       uplink lost (sustained) -> RTL engaged (auto)")
            else:
                self.log(f"COMMAND_ACK    DO_SET_MODE custom_mode={hb.custom_mode} result=ACCEPTED")
        if self.prev_armed is not None and armed != self.prev_armed:
            self.log("HEARTBEAT      base_mode +SAFETY_ARMED -> MOTORS ARMED" if armed
                     else "HEARTBEAT      base_mode -SAFETY_ARMED -> disarmed")
        if g:
            lat, lon = g.lat / 1e7, g.lon / 1e7
            if self.prev_pos and (abs(lat - self.prev_pos[0]) > 0.5 or abs(lon - self.prev_pos[1]) > 0.5):
                d = demo.haversine_km(self.prev_pos[0], self.prev_pos[1], lat, lon)
                self.log(f"GLOBAL_POSITION_INT lat={lat:.4f} lon={lon:.4f}  (delta {d:,.0f} km)")
            self.prev_pos = (lat, lon)
        if up != self.prev_up:
            self.log(f"link           downlink OK — {c.rate()} msg/s" if up
                     else "link           telemetry timeout — no downlink")
            self.prev_up = up

        if not up:
            if now - self.t_tel >= 1.1:
                self.log("failsafe       GCS/RC link lost -> RTL / LAND"); self.t_tel = now
        elif now - self.t_tel >= 0.9:
            opts = []
            if hb: opts.append(f"HEARTBEAT      QUADROTOR/ARDUPILOTMEGA base=0x{hb.base_mode:02X} "
                               f"mode={hb.custom_mode} MAV_STATE_ACTIVE")
            if g: opts.append(f"GLOBAL_POSITION_INT lat={g.lat/1e7:.4f} lon={g.lon/1e7:.4f} "
                              f"alt={g.alt/1000:.0f}m rel={g.relative_alt/1000:.0f}m")
            if ss: opts.append(f"SYS_STATUS     volt={ss.voltage_battery/1000:.1f}V "
                               f"cur={ss.current_battery/100:.1f}A batt={ss.battery_remaining}% load=0.5%")
            if at: opts.append(f"ATTITUDE       roll={math.degrees(at.roll):.0f} "
                               f"pitch={math.degrees(at.pitch):.0f} yaw={math.degrees(at.yaw):.0f} deg")
            if opts:
                self.log(opts[self.cyc % len(opts)]); self.cyc += 1
            self.t_tel = now

        self.prev_armed = armed
        if hb: self.prev_mode = hb.custom_mode

    def lines(self):
        return [f"{t}  {m}" for t, m in self.buf]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=14550)
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    a = ap.parse_args()

    hub = MavHub(port=a.port); hub.start()
    stub = DroneStub(conn_str=f"udpout:127.0.0.1:{a.port}", failsafe_timeout=4.0).start()
    client = ClientLink(f"udpout:127.0.0.1:{a.port}")
    hw = hw_check()
    blog = BackendLog(client)
    blog.log("boot           flight software online — MAVLink 2 @ 10 Hz")
    blog.log("sensors        IMU ok  baro ok  GNSS fix=3D")

    first = True; t0 = time.time()
    if not a.plain: hide_cursor()
    try:
        while True:
            blog.tick()
            txt = frame_drone(hw, client, blog.lines())
            if a.plain:
                print(txt); print()
            else:
                draw(txt, first); first = False
            if a.seconds and time.time() - t0 >= a.seconds:
                break
            time.sleep(1 / 8)
    except KeyboardInterrupt:
        pass
    finally:
        if not a.plain: show_cursor()
        client.close(); stub.stop(); hub.stop()


if __name__ == "__main__":
    main()
