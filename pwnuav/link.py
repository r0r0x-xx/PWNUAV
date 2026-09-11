"""Transport-agnostic MAVLink link helpers for PWNUAV tools."""
from __future__ import annotations

import time

from pymavlink import mavutil


def connect(conn_str: str, source_system: int = 255,
            source_component: int = 190):
    """Open a MAVLink connection.

    conn_str is any mavutil string, e.g. 'udpout:127.0.0.1:14550'
    (attacker tool against the DroneStub) or 'udpin:127.0.0.1:14550'
    (attacker tool against ArduPilot SITL --out). Default source id
    255/190 is a ground control station identity.
    """
    return mavutil.mavlink_connection(
        conn_str,
        source_system=source_system,
        source_component=source_component,
    )


def announce(master, count: int = 3, interval: float = 0.2) -> None:
    """Send a few GCS heartbeats so a 'udpin' peer learns our address."""
    for _ in range(count):
        master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0,
        )
        time.sleep(interval)


def wait_heartbeat(master, timeout: float = 10.0):
    """Block until a HEARTBEAT arrives; return it or None on timeout."""
    return master.wait_heartbeat(timeout=timeout)
