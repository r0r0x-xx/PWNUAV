"""Shared TUI dashboard for the PWNUAV attack demos.

FIXED `top`-style screen: refreshes in place (no scrolling), with HARDWARE,
DRONE (ASCII, reacts to the attack) and attack ACTIVITY (backend) panels. Each
PoC assembles its dashboard from these helpers. Local UDP link against the
DroneStub (a live, stateful drone), with a check of the real SDR hardware.
"""
from __future__ import annotations

import collections
import math
import os
import socket
import sys
import threading
import time

os.environ.setdefault("MAVLINK20", "1")

from pymavlink import mavutil

from pwnuav import demo
from pwnuav.drone_stub import DroneStub
from pwnuav.link import announce, connect

W = 92                                   # fixed dashboard width
HOME_LAT, HOME_LON = 37.774900, -122.419400

QUAD = [
    r"   (o)===|===(o)   ",
    r"      \\  |  //     ",
    r"       [ PWN ]      ",
    r"      //  |  \\     ",
    r"   (o)===|===(o)   ",
]

# ---------------- ANSI (flicker-free refresh) ----------------
def draw(text: str, first: bool = False) -> None:
    lines = text.split("\n")
    width = max((len(l) for l in lines), default=0)
    out = ["\033[2J" if first else "", "\033[H"]
    for l in lines:
        out.append(l.ljust(width) + "\033[K")
    out.append("\033[J")
    sys.stdout.write("\n".join(out)); sys.stdout.flush()

def hide_cursor(): sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\033[?25h\n"); sys.stdout.flush()

# ---------------- hardware check ----------------
def hw_check():
    """Return rows (label, ok:bool, detail) for the SDR radios.

    By default hides serials/URIs (for recording public demos): shows
    'connected'. With PWNUAV_HW_VERBOSE=1 it shows the serial/URI (for debugging)."""
    verbose = bool(os.environ.get("PWNUAV_HW_VERBOSE"))
    rows = []
    try:
        import SoapySDR
        found = {}
        for a in SoapySDR.Device.enumerate():
            d = dict(a); found[d.get("driver")] = d
        for label, key in [("ADALM-Pluto  (drone/attacker TX)", "plutosdr"),
                           ("RTL-SDR      (receiver RX)", "rtlsdr"),
                           ("HackRF       (jammer TX)", "hackrf")]:
            ok = key in found
            if not ok:
                det = "not detected"
            elif verbose:
                det = (found[key].get("label") or found[key].get("uri") or "")[:34]
            else:
                det = "connected"
            rows.append((label, ok, det))
    except Exception:
        rows.append(("SoapySDR", False, "unavailable (use .venv-radio)"))
    return rows

# ---------------- activity log (ring buffer) ----------------
class Activity:
    def __init__(self, n=15):
        self.buf = collections.deque(maxlen=n)
    def log(self, msg: str):
        self.buf.append((time.strftime("%H:%M:%S"), msg))
    def lines(self, n=15):
        rows = list(self.buf)[-n:]
        return [f"{t}  {m}" for t, m in rows]

# ---------------- drone link (DroneStub + poller) ----------------
def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

class DroneLink:
    """Brings up the DroneStub and a connection; polls telemetry in the background."""
    def __init__(self):
        self.port = _free_port()
        self.stub = DroneStub(conn_str=f"udpin:127.0.0.1:{self.port}").start()
        self.m = connect(f"udpout:127.0.0.1:{self.port}")
        announce(self.m)
        try:
            self.m.wait_heartbeat(timeout=5)
        except Exception:
            pass
        self.last = {}
        self._rate = collections.deque(maxlen=30)
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True); self._t.start()

    def _run(self):
        while not self._stop.is_set():
            msg = self.m.recv_match(blocking=True, timeout=0.2)
            if msg and msg.get_type() != "BAD_DATA":
                self.last[msg.get_type()] = msg
                self._rate.append(time.time())

    @property
    def state(self):
        return self.stub.state

    def rate(self):
        now = time.time()
        recent = [t for t in self._rate if now - t < 1.0]
        return len(recent)

    def link_up(self):
        return self.rate() > 0

    def close(self):
        self._stop.set(); self._t.join(timeout=1)
        try: self.m.close()
        except Exception: pass
        self.stub.stop()

class ClientLink:
    """Connects to an ALREADY-running drone (Terminal 1) via the hub. Hosts no stub.
    The attack (Terminal 2) uses this to inject and observe telemetry."""
    def __init__(self, conn_str="udpout:127.0.0.1:14550", capture_path=None):
        self.conn_str = conn_str
        self.m = connect(conn_str)
        announce(self.m)
        try:
            self.m.wait_heartbeat(timeout=5)
        except Exception:
            pass
        self.last = {}
        self.counts = collections.Counter()   # messages seen per type (evidence)
        self.total = 0
        # raw capture to file (bytes of each MAVLink frame, exactly as they arrive)
        self.capture_path = capture_path
        self.saved = 0
        self._cap = open(capture_path, "wb") if capture_path else None
        self._rate = collections.deque(maxlen=60)
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True); self._t.start()

    def _run(self):
        last_ka = 0.0
        while not self._stop.is_set():
            now = time.time()
            if now - last_ka > 2.0:      # keepalive: the hub expires silent peers (TTL)
                try:
                    self.m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                                              mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
                except Exception:
                    pass
                last_ka = now
            msg = self.m.recv_match(blocking=True, timeout=0.2)
            if msg and msg.get_type() != "BAD_DATA":
                self.last[msg.get_type()] = msg
                self.counts[msg.get_type()] += 1
                self.total += 1
                self._rate.append(time.time())
                if self._cap is not None:
                    try:
                        self._cap.write(bytes(msg.get_msgbuf())); self.saved += 1
                    except Exception:
                        pass

    def rate(self):
        now = time.time(); return len([t for t in self._rate if now - t < 1.0])

    def link_up(self):
        return self.rate() > 0

    def armed(self):
        hb = self.last.get("HEARTBEAT")
        return bool(hb) and "ARMED" in demo.base_mode_flags(hb.base_mode)

    @property
    def mav(self):
        return self.m.mav

    def close(self):
        self._stop.set(); self._t.join(timeout=1)
        try: self.m.close()
        except Exception: pass
        if self._cap is not None:
            try: self._cap.flush(); self._cap.close()
            except Exception: pass

# ---------------- drone render (ASCII + state) ----------------
def _batt_bar(pct, n=16):
    f = int(round(pct / 100 * n)); return "[" + "#" * f + "-" * (n - f) + f"] {pct}%"

def _minimap(dlat, dlon, w=44, h=7):
    lats = [HOME_LAT, dlat]; lons = [HOME_LON, dlon]
    la0, la1 = min(lats), max(lats); lo0, lo1 = min(lons), max(lons)
    dla = (la1 - la0) or 0.5; dlo = (lo1 - lo0) or 0.5
    la0 -= dla * .25; la1 += dla * .25; lo0 -= dlo * .25; lo1 += dlo * .25
    grid = [[" "] * w for _ in range(h)]
    def place(lat, lon, ch):
        x = int((lon - lo0) / (lo1 - lo0) * (w - 1)); y = int((la1 - lat) / (la1 - la0) * (h - 1))
        grid[max(0, min(h - 1, y))][max(0, min(w - 1, x))] = ch
    place(HOME_LAT, HOME_LON, "H"); place(dlat, dlon, "D")
    return ["+" + "-" * w + "+"] + ["|" + "".join(r) + "|" for r in grid] + ["+" + "-" * w + "+"]

def drone_lines(link: DroneLink):
    last = link.last
    hb = last.get("HEARTBEAT"); g = last.get("GLOBAL_POSITION_INT"); ss = last.get("SYS_STATUS")
    dlat = g.lat / 1e7 if g else HOME_LAT; dlon = g.lon / 1e7 if g else HOME_LON
    up = link.link_up()
    armed = bool(hb) and "ARMED" in demo.base_mode_flags(hb.base_mode)
    L = list(QUAD)
    L.append("")
    mode_txt = ""
    if hb:
        mode_txt = f"   mode {hb.custom_mode}" + (" (RTL/FAILSAFE)" if hb.custom_mode == 6 else "")
    L.append(f"status : {'>>> ARMED <<<' if armed else 'DISARMED'}" + mode_txt)
    L.append(f"pos    : lat {dlat:8.4f}  lon {dlon:9.4f}"
             + (f"  alt {g.alt/1000:.0f} m" if g else ""))
    if ss: L.append(f"batt   : {ss.voltage_battery/1000:.1f} V  {_batt_bar(ss.battery_remaining)}")
    if up:
        L.append(f"link   : OK  ~{link.rate()} msg/s")
    else:
        L.append("link   : *** LOST -> FAILSAFE (RTL/LAND) ***")
    dist = demo.haversine_km(HOME_LAT, HOME_LON, dlat, dlon)
    L.append("")
    L += _minimap(dlat, dlon)
    L.append(f"drone-home: {dist:,.0f} km")
    return L

def target_lines(client):
    """Compact target status (for the ATTACKER panel, Terminal 2)."""
    hb = client.last.get("HEARTBEAT"); g = client.last.get("GLOBAL_POSITION_INT")
    dlat = g.lat / 1e7 if g else HOME_LAT; dlon = g.lon / 1e7 if g else HOME_LON
    dist = demo.haversine_km(HOME_LAT, HOME_LON, dlat, dlon)
    L = [f"sysid=1  {'>>> ARMED <<<' if client.armed() else 'DISARMED'}"
         + (f"  mode {hb.custom_mode}" if hb else "")]
    L.append(f"pos  lat {dlat:.4f}  lon {dlon:.4f}   dist_home {dist:,.0f} km")
    L.append("link " + (f"OK ~{client.rate()} msg/s" if client.link_up()
                        else "*** LOST -> FAILSAFE (RTL/LAND) ***"))
    return L

# ---------------- fixed dashboard assembly ----------------
def _bar(title=""):
    if not title:
        return "+" + "-" * (W - 2) + "+"
    t = f"[ {title} ]"
    return "+" + "-" * 2 + t + "-" * (W - 4 - len(t)) + "+"

def _row(s=""):
    return "| " + s[:W - 4].ljust(W - 4) + " |"

def frame(poc_title, status, hw_rows, link, activity, extra=None):
    """Return the full dashboard text (fixed screen)."""
    L = []
    L.append(_bar())
    L.append(_row(f"PWNUAV · {poc_title}".ljust(W - 18) + f"[ {status} ]"))
    L.append(_bar("HARDWARE"))
    for label, ok, det in hw_rows:
        mark = "OK " if ok else "-- "
        L.append(_row(f"{mark} {label:<34} {det}"))
    L.append(_bar("TARGET (drone via link)"))
    for l in target_lines(link):
        L.append(_row(l))
    if extra:
        L.append(_bar(extra[0]))
        for l in extra[1]:
            L.append(_row(l))
    L.append(_bar("ATTACK ACTIVITY"))
    for l in activity.lines():
        L.append(_row(l))
    L.append(_bar())
    return "\n".join(L)

def frame_drone(hw_rows, client, log_lines=None):
    """Terminal 1 dashboard: DRONE EMULATOR console (live telemetry)."""
    L = []
    L.append(_bar())
    L.append(_row("PWNUAV DRONE EMULATOR — live MAVLink 2 link (signing OFF)"))
    L.append(_bar("HARDWARE"))
    for label, ok, det in hw_rows:
        L.append(_row(("OK " if ok else "-- ") + f"{label:<34} {det}"))
    L.append(_bar("STATE"))
    for l in drone_lines(client):
        L.append(_row(l))
    L.append(_bar("TELEMETRY / EVENTS"))
    for l in (log_lines or []):
        L.append(_row(l))
    L.append(_bar())
    return "\n".join(L)

# ---------------- timed step sequence ----------------
class Steps:
    """Runs events (t_seconds, function) exactly once when their time arrives.
    `done` once the last event has passed + a tail."""
    def __init__(self, events, tail=1.0):
        self.events = sorted(events, key=lambda e: e[0])
        self.tail = tail
        self.i = 0
    def __call__(self, t):
        while self.i < len(self.events) and t >= self.events[self.i][0]:
            try:
                self.events[self.i][1]()
            except Exception:
                pass
            self.i += 1
        last = self.events[-1][0] if self.events else 0
        return self.i >= len(self.events) and t >= last + self.tail

# ---------------- fixed refresh loop ----------------
def run_dashboard(poc_title, hw_rows, link, activity, step, total=None,
                  hz=8, plain=False, extra_fn=None):
    """Runs the fixed dashboard. `step(t)` advances the attack each tick and may
    log to `activity`; returns 'done' when finished (or uses `total` seconds)."""
    period = 1.0 / hz
    t0 = time.time(); first = True; status = "RUNNING"
    if not plain: hide_cursor()
    try:
        while True:
            t = time.time() - t0
            done = step(t)
            if done or (total is not None and t >= total):
                status = "DONE"
            extra = extra_fn() if extra_fn else None
            txt = frame(poc_title, status, hw_rows, link, activity, extra)
            if plain:
                print(txt); print()
            else:
                draw(txt, first=first); first = False
            if status == "DONE":
                # one last refresh and exit
                time.sleep(0.4)
                if not plain:
                    extra = extra_fn() if extra_fn else None
                    draw(frame(poc_title, "DONE", hw_rows, link, activity, extra))
                break
            time.sleep(period)
    finally:
        if not plain: show_cursor()
