"""MAVLink UDP fan-out hub for the PWNUAV interactive demos.

A simple UDP reflector: the drone, monitor and attacker all connect with
`udpout:127.0.0.1:<port>`; the hub learns each address and forwards every
datagram to all the OTHER peers. This way the drone's downlink reaches the
monitor AND the attacker at once, and the attacker's commands reach the drone —
something a single pymavlink `udpin` socket does not do (it only talks to the
last peer).

Usage:
  python -m pwnuav.mav_hub --port 14550
"""
from __future__ import annotations

import argparse
import socket
import threading
import time


class MavHub:
    def __init__(self, host: str = "127.0.0.1", port: int = 14550,
                 peer_ttl: float = 30.0, jam_pps: int = 3000):
        self.host, self.port, self.peer_ttl = host, port, peer_ttl
        self.jam_pps = jam_pps         # flood threshold above which the channel counts as jammed
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.settimeout(0.2)
        self.peers: dict[tuple, float] = {}
        self.jammed = False            # the channel is saturated by a flood (jamming)
        self.on_peer = None            # callback(addr) when a new peer joins
        self.on_jam = None             # callback(bool) when the jamming state changes
        self._counts: dict[tuple, int] = {}
        self._win_start = time.time()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def start(self) -> "MavHub":
        self._t.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._t.join(timeout=1.0)
        try:
            self.sock.close()
        except OSError:
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data, src = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if src not in self.peers and self.on_peer:
                try:
                    self.on_peer(src)
                except Exception:
                    pass
            self.peers[src] = time.time()
            now = time.time()

            # --- jamming detection: measure per-peer rate in 0.25s windows ---
            self._counts[src] = self._counts.get(src, 0) + 1
            win = now - self._win_start
            if win >= 0.25:
                jammed = any((c / win) > self.jam_pps for c in self._counts.values())
                if jammed != self.jammed:
                    self.jammed = jammed
                    if self.on_jam:
                        try:
                            self.on_jam(jammed)
                        except Exception:
                            pass
                self._counts.clear()
                self._win_start = now

            for p in [p for p, t in self.peers.items() if now - t > self.peer_ttl]:
                del self.peers[p]

            # Channel saturated (jamming): the shared medium carries no legitimate traffic.
            if self.jammed:
                continue

            for p in list(self.peers):
                if p != src:
                    try:
                        self.sock.sendto(data, p)
                    except OSError:
                        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="PWNUAV MAVLink fan-out hub")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=14550)
    args = ap.parse_args()
    hub = MavHub(args.host, args.port)
    hub.on_peer = lambda s: print(f"[hub] peer connected {s[0]}:{s[1]}  (total {len(hub.peers)})", flush=True)
    hub.start()
    print(f"[hub] MAVLink fan-out listening on {args.host}:{args.port} — Ctrl-C to exit", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        hub.stop()


if __name__ == "__main__":
    main()
