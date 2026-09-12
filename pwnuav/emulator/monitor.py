#!/usr/bin/env python3
"""PWNUAV emulator console: quad ASCII art, status, mini-map and (optional) live TUI.

Usage:
  python pwnuav/emulator/monitor.py                 # static snapshot
  python pwnuav/emulator/monitor.py --live          # live TUI dashboard (Ctrl-C to exit)
  python pwnuav/emulator/monitor.py --live --spoof  # live + injects a GPS spoof; watch the drone jump
  python pwnuav/emulator/monitor.py --live --seconds 8   # bounded live run (to record/test)
"""
from __future__ import annotations
import os; os.environ.setdefault("MAVLINK20","1")
import sys, socket, time, math, argparse, collections
from pwnuav.drone_stub import DroneStub
from pwnuav.link import connect, announce
from pwnuav.gps_spoof import spoof_position
from pwnuav import demo

QUAD = [
 r"      (o)========|========(o)      ",
 r"         \\      |      //         ",
 r"           \\  [ ^ ]  //           ",
 r"            >--| PWN |--<          ",
 r"           //  [___]  \\           ",
 r"         //      |      \\         ",
 r"      (o)========|========(o)      ",
]
HOME_LAT, HOME_LON = 37.774900, -122.419400   # 'real' position of the emulated drone

def _port():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("127.0.0.1",0)); p=s.getsockname()[1]; s.close(); return p

def batt_bar(pct, n=20):
    fill=int(round(pct/100*n)); return "["+"#"*fill+"-"*(n-fill)+f"] {pct}%"

def minimap(home, drone, w=46, h=11):
    lats=[home[0],drone[0]]; lons=[home[1],drone[1]]
    latmin,latmax=min(lats),max(lats); lonmin,lonmax=min(lons),max(lons)
    dlat=(latmax-latmin) or 0.5; dlon=(lonmax-lonmin) or 0.5
    latmin-=dlat*0.25; latmax+=dlat*0.25; lonmin-=dlon*0.25; lonmax+=dlon*0.25
    grid=[[" "]*w for _ in range(h)]
    def place(lat,lon,ch):
        x=int((lon-lonmin)/(lonmax-lonmin)*(w-1)); y=int((latmax-lat)/(latmax-latmin)*(h-1))
        x=max(0,min(w-1,x)); y=max(0,min(h-1,y)); grid[y][x]=ch
    place(*home,"H"); place(*drone,"D")
    top="+"+"-"*w+"+"
    return [top]+["|"+"".join(r)+"|" for r in grid]+[top]

def _draw(text, first=False):
    """Flicker-free refresh: moves the cursor to Home and overwrites each
    line (padding + clear-to-EOL) instead of clearing the whole screen."""
    lines = text.split("\n")
    width = max((len(l) for l in lines), default=0)
    out = ["\033[2J" if first else "", "\033[H"]
    for l in lines:
        out.append(l.ljust(width) + "\033[K")
    out.append("\033[J")                 # clear anything left below
    sys.stdout.write("\n".join(out))
    sys.stdout.flush()

def render(last, seen, port, secs, spoof_note="", link_lost=False):
    hb=last.get("HEARTBEAT"); g=last.get("GLOBAL_POSITION_INT"); a=last.get("ATTITUDE"); ss=last.get("SYS_STATUS")
    dlat=g.lat/1e7 if g else HOME_LAT; dlon=g.lon/1e7 if g else HOME_LON
    armed = bool(hb) and "ARMED" in demo.base_mode_flags(hb.base_mode)
    L=[]
    L+= QUAD
    L.append("="*46)
    L.append(" PWNUAV EMULATOR — vulnerable-by-design MAVLink drone")
    L.append("="*46)
    L.append(f" transport : udp 127.0.0.1:{port}   MAVLink v2 (0xFD)   signing: OFF")
    L.append("-"*46)
    L.append(f" status    : {'>>> ARMED <<<' if armed else 'DISARMED'}"
             + (f"   mode custom={hb.custom_mode}" if hb else ""))
    if hb: L.append(f" flags     : [{'|'.join(demo.base_mode_flags(hb.base_mode))}]   {demo.enum_name('MAV_STATE',hb.system_status)}")
    L.append(f" position  : lat {dlat:.6f}  lon {dlon:.6f}" + (f"  alt {g.alt/1000:.1f} m" if g else ""))
    if a: L.append(f" attitude  : roll {math.degrees(a.roll):5.1f}  pitch {math.degrees(a.pitch):5.1f}  yaw {math.degrees(a.yaw):5.1f} deg")
    if ss: L.append(f" battery   : {ss.voltage_battery/1000:.1f} V  "+batt_bar(ss.battery_remaining))
    rate=sum(seen.values())/max(secs,0.1)
    if link_lost:
        L.append(" link      : *** LOST — no telemetry -> FAILSAFE (RTL/LAND) ***")
    else:
        L.append(f" link      : telemetry OK — {rate:.0f} msg/s")
    L.append("-"*46)
    L.append(" MAP (H=home  D=drone)")
    dist=demo.haversine_km(HOME_LAT,HOME_LON,dlat,dlon)
    for row in minimap((HOME_LAT,HOME_LON),(dlat,dlon)): L.append(" "+row)
    L.append(f" drone-home distance: {dist:,.0f} km")
    if spoof_note: L.append(" "+spoof_note)
    L.append("="*46)
    return "\n".join(L)

def collect(m, dur):
    seen=collections.Counter(); last={}; t0=time.time()
    while time.time()-t0<dur:
        msg=m.recv_match(blocking=True,timeout=0.2)
        if msg and msg.get_type()!="BAD_DATA":
            seen[msg.get_type()]+=1; last[msg.get_type()]=msg
    return seen,last

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--live",action="store_true"); ap.add_argument("--spoof",action="store_true")
    ap.add_argument("--seconds",type=float,default=None)
    ap.add_argument("--connect",default=None,
                    help="attach to an already-running drone, e.g. udpout:127.0.0.1:14550 "
                         "(interactive demo). Without this, the monitor spins up its own drone.")
    args=ap.parse_args()

    external = args.connect is not None
    if external:
        stub=None; conn=args.connect
        # the displayed 'port' is pulled from conn_str when possible
        try: port=int(conn.rsplit(":",1)[1])
        except Exception: port=0
    else:
        port=_port(); stub=DroneStub(conn_str=f"udpin:127.0.0.1:{port}").start()
        conn=f"udpout:127.0.0.1:{port}"
    try:
        m=connect(conn); announce(m)
        try: m.wait_heartbeat(timeout=5)
        except Exception: pass
        if not args.live:
            seen,last=collect(m,2.0); print(render(last,seen,port,2.0)); m.close(); return
        end=time.time()+(args.seconds if args.seconds else 3600); spoofed=False; note=""
        t0=time.time(); lastmsg=time.time(); sys.stdout.write("\033[?25l"); sys.stdout.flush()
        keep={}
        while time.time()<end:
            seen,last=collect(m,0.4)
            keep.update(last)                       # keep last state even if the link goes quiet
            if seen: lastmsg=time.time()
            link_lost = (time.time()-lastmsg) > 1.5
            el=time.time()-t0
            if args.spoof and not spoofed and el>3.5:
                for _ in range(10): spoof_position(m,6.2518,-75.5636,1500)
                spoofed=True; note=">>> GPS SPOOF INJECTED (GPS_INPUT -> Medellin) <<<"
            _draw(render(keep,seen,port,0.4,note,link_lost=link_lost), first=(el < 0.5))
        m.close()
    except KeyboardInterrupt:
        pass
    finally:
        if args.live:
            sys.stdout.write("\033[?25h\n"); sys.stdout.flush()
        if stub is not None: stub.stop()

if __name__=="__main__":
    main()
