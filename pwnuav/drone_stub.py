"""PWNUAV drone stub.

A minimal vulnerable-by-design MAVLink vehicle endpoint for tests and local
development. Speaks the same MAVLink an ArduPilot SITL would, with NO
MAVLink2 signing (intentionally insecure).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from pymavlink import mavutil


@dataclass
class DroneState:
    armed: bool = False
    custom_mode: int = 0
    received_commands: list = field(default_factory=list)
    spoofed_lat: int | None = None      # lat * 1e7
    spoofed_lon: int | None = None      # lon * 1e7
    spoofed_alt_mm: int | None = None   # alt in mm
    link_up: bool = True                # False = link denied (jamming); no telemetry emitted
    failsafe: bool = False              # sustained uplink loss -> RTL (stays compromised)


class DroneStub:
    def __init__(self, conn_str: str = "udpin:127.0.0.1:14550",
                 system_id: int = 1, component_id: int = 1,
                 failsafe_timeout: float | None = None):
        self.master = mavutil.mavlink_connection(
            conn_str, source_system=system_id, source_component=component_id,
        )
        self.state = DroneState()
        # failsafe: no GCS heartbeat for > timeout s -> RTL (None = disabled)
        self.failsafe_timeout = failsafe_timeout
        self._last_gcs = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> "DroneStub":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)
        self.master.close()

    def _run(self) -> None:
        last_tx = 0.0
        while not self._stop.is_set():
            msg = self.master.recv_match(blocking=True, timeout=0.1)
            if msg is not None:
                self._handle(msg)
            now = time.time()
            # failsafe on sustained uplink loss (e.g. jamming): commit to RTL
            if (self.failsafe_timeout and not self.state.failsafe
                    and now - self._last_gcs > self.failsafe_timeout):
                self.state.failsafe = True
                self.state.custom_mode = 6            # ArduCopter RTL
            if now - last_tx >= 0.1:  # 10 Hz telemetry
                self._emit_telemetry()
                last_tx = now

    def _emit_telemetry(self) -> None:
        if not self.state.link_up:      # link denied (jamming): downlink down
            return
        base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        if self.state.armed:
            base_mode |= mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        self.master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode, self.state.custom_mode,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        ts = int(time.time() * 1000) & 0xFFFFFFFF
        lat = self.state.spoofed_lat if self.state.spoofed_lat is not None else 377749000
        lon = self.state.spoofed_lon if self.state.spoofed_lon is not None else -1224194000
        alt = self.state.spoofed_alt_mm if self.state.spoofed_alt_mm is not None else 100000
        self.master.mav.global_position_int_send(
            ts,
            lat, lon,                # lat, lon (deg * 1e7)
            alt, 50000,              # alt, relative_alt (mm)
            0, 0, 0, 0,              # vx, vy, vz (cm/s), hdg
        )
        self.master.mav.attitude_send(
            ts, 0.01, 0.02, 1.57, 0.0, 0.0, 0.0,
        )
        self.master.mav.sys_status_send(
            0, 0, 0, 500,       # sensors present/enabled/health, load (0.5%)
            12000, 1800, 75,    # voltage (mV), current (cA), remaining (%)
            0, 0, 0, 0, 0, 0,   # drop_rate_comm, errors_comm, errors_count1..4
        )

    def _handle(self, msg) -> None:
        t = msg.get_type()
        if t == "HEARTBEAT" and msg.type == mavutil.mavlink.MAV_TYPE_GCS:
            self._last_gcs = time.time()      # GCS uplink alive -> no failsafe
        if t == "COMMAND_LONG":
            self.state.received_commands.append(msg)
            if msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                self.state.armed = int(msg.param1) == 1
                self._ack(msg.command)
            elif msg.command == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
                self.state.custom_mode = int(msg.param2)
                self._ack(msg.command)
        elif t == "SET_MODE":
            self.state.custom_mode = int(msg.custom_mode)
        elif t == "GPS_INPUT":
            self.state.spoofed_lat = int(msg.lat)
            self.state.spoofed_lon = int(msg.lon)
            self.state.spoofed_alt_mm = int(msg.alt * 1000)

    def _ack(self, command: int) -> None:
        self.master.mav.command_ack_send(
            command, mavutil.mavlink.MAV_RESULT_ACCEPTED,
        )
