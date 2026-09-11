"""PWNUAV drone service for the interactive demos (Terminal 2).

Brings up the vulnerable-by-design drone link:
  - a MAVLink UDP fan-out hub (so the monitor and attacker share the link)
  - the DroneStub (a live, stateful drone: armed, mode, position) on that hub
  - an IMPACT LOG that reacts live to the attacks: arm, GPS jump,
    commands received, and link loss (jamming).

Usage:
  python -m pwnuav.drone_service                 # port 14550
  python -m pwnuav.drone_service --port 14550
The monitor (Terminal 1) and the attack (Terminal 3) connect to:
  udpout:127.0.0.1:14550
"""
from __future__ import annotations

import os
os.environ.setdefault("MAVLINK20", "1")
import argparse
import time

from pwnuav import demo
from pwnuav.drone_stub import DroneStub
from pwnuav.mav_hub import MavHub

HOME_LAT, HOME_LON = 37.774900, -122.419400


def _pos(state):
    lat = (state.spoofed_lat if state.spoofed_lat is not None else 377749000) / 1e7
    lon = (state.spoofed_lon if state.spoofed_lon is not None else -1224194000) / 1e7
    return lat, lon


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV drone service (hub + DroneStub)")
    ap.add_argument("--port", type=int, default=14550)
    args = ap.parse_args()

    hub = MavHub(port=args.port)
    hub.on_peer = lambda s: print(f"  [link] peer connected {s[0]}:{s[1]}", flush=True)
    hub.on_jam = lambda j: print(
        "\n  *** [IMPACT] RF JAMMING — channel saturated, DOWNLINK LOST -> failsafe ***"
        if j else "  [link] jamming cleared — telemetry restored", flush=True)
    hub.start()
    stub = DroneStub(conn_str=f"udpout:127.0.0.1:{args.port}").start()

    print("=" * 60, flush=True)
    print(" PWNUAV DRONE SERVICE — vulnerable-by-design MAVLink drone", flush=True)
    print("=" * 60, flush=True)
    print(f" link     : udp 127.0.0.1:{args.port}   MAVLink 2 (0xFD)   signing: OFF", flush=True)
    print(" telemetry: HEARTBEAT · GLOBAL_POSITION_INT · ATTITUDE · SYS_STATUS @10 Hz", flush=True)
    print(" point the monitor and the attack at  ->  udpout:127.0.0.1:%d" % args.port, flush=True)
    print("-" * 60, flush=True)
    print(" [status] waiting... (Ctrl-C to stop)", flush=True)

    st = stub.state
    prev_armed = st.armed
    prev_spoof = (st.spoofed_lat, st.spoofed_lon)
    prev_mode = st.custom_mode
    prev_cmds = len(st.received_commands)
    last_status = 0.0
    try:
        while True:
            time.sleep(0.3)
            armed = st.armed
            spoof = (st.spoofed_lat, st.spoofed_lon)
            mode = st.custom_mode
            cmds = len(st.received_commands)
            lat, lon = _pos(st)
            dist = demo.haversine_km(HOME_LAT, HOME_LON, lat, lon)

            # --- impact events ---
            if cmds > prev_cmds:
                last = st.received_commands[-1]
                src = getattr(last, "_header", None)
                srcsys = last.get_srcSystem() if hasattr(last, "get_srcSystem") else "?"
                print(f"\n  >> [C2] COMMAND_LONG received from sysid={srcsys} "
                      f"(unverified GCS) cmd={last.command}", flush=True)
            if armed != prev_armed:
                if armed:
                    print("  *** [IMPACT] DRONE ARMED by UNAUTHENTICATED command "
                          "-> motors enabled ***", flush=True)
                else:
                    print("  *** [IMPACT] DRONE DISARMED by external command ***", flush=True)
            if mode != prev_mode:
                print(f"  *** [IMPACT] FLIGHT MODE changed -> custom_mode={mode} "
                      "(external injection) ***", flush=True)
            if spoof != prev_spoof and st.spoofed_lat is not None:
                print(f"  *** [IMPACT] POSITION HIJACKED -> {lat:.4f},{lon:.4f} "
                      f"(~{dist:,.0f} km via spoofed GPS_INPUT) ***", flush=True)

            # --- periodic status line ---
            now = time.time()
            if now - last_status >= 1.0:
                a = "ARMED" if armed else "disarmed"
                print(f"  [status] {a}  mode={mode}  pos=({lat:.4f},{lon:.4f})  "
                      f"dist_home={dist:,.0f} km  batt=75%  cmds={cmds}", flush=True)
                last_status = now

            prev_armed, prev_spoof, prev_mode, prev_cmds = armed, spoof, mode, cmds
    except KeyboardInterrupt:
        pass
    finally:
        stub.stop()
        hub.stop()
        print("\n[drone] service stopped.", flush=True)


if __name__ == "__main__":
    main()
