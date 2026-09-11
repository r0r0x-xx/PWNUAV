"""Shared helpers for the attack demos (emulated-drone telemetry)."""
from __future__ import annotations
import math
import numpy as np
from pymavlink import mavutil
from pwnuav.rf.gfsk import FS, modulate, bytes_to_bits
from pwnuav.rf.framing import build_frame

M = mavutil.mavlink

def telemetry_messages(mav):
    """Realistic telemetry cycle emitted by the emulated drone (vulnerable-by-design)."""
    return [
        ("HEARTBEAT", mav.heartbeat_encode(M.MAV_TYPE_QUADROTOR, M.MAV_AUTOPILOT_ARDUPILOTMEGA,
                                           M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, M.MAV_STATE_ACTIVE)),
        ("SYS_STATUS", mav.sys_status_encode(0, 0, 0, 412, 12000, 1800, 75, 0, 0, 0, 0, 0, 0)),
        ("GPS_RAW_INT", mav.gps_raw_int_encode(0, 3, 377749000, -1224194000, 100000, 121, 200, 350, 9000, 11)),
        ("GLOBAL_POSITION_INT", mav.global_position_int_encode(0, 377749000, -1224194000, 100000, 50000, 120, -35, 5, 9000)),
        ("ATTITUDE", mav.attitude_encode(0, 0.0123, 0.0210, 1.5708, 0.001, 0.002, 0.0)),
        ("VFR_HUD", mav.vfr_hud_encode(12.4, 12.9, 90, 55, 100.0, 0.4)),
    ]

def downlink_iq(messages, mav, reps=20, gap_div=500):
    gap = np.zeros(FS // gap_div, np.complex64)
    iqs = [modulate(bytes_to_bits(build_frame(m.pack(mav)))) for (_, m) in messages]
    unit = np.concatenate([np.concatenate([x, gap]) for x in iqs])
    return np.tile(unit, reps).astype(np.complex64), max(len(x) for x in iqs)

def hexdump(b, width=16, indent="  "):
    b = bytes(b); out = []
    for i in range(0, len(b), width):
        chunk = b[i:i + width]
        hexs = " ".join(f"{x:02X}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        out.append(f"{indent}{i:04X}  {hexs:<{width*3}}  {asc}")
    return "\n".join(out)

def enum_name(enum, val):
    try:
        return mavutil.mavlink.enums[enum][val].name
    except Exception:
        return "?"

def base_mode_flags(bm):
    flags = [
        (M.MAV_MODE_FLAG_SAFETY_ARMED, "ARMED"),
        (M.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED, "MANUAL"),
        (M.MAV_MODE_FLAG_STABILIZE_ENABLED, "STABILIZE"),
        (M.MAV_MODE_FLAG_GUIDED_ENABLED, "GUIDED"),
        (M.MAV_MODE_FLAG_AUTO_ENABLED, "AUTO"),
        (M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, "CUSTOM_MODE"),
    ]
    return [n for (bit, n) in flags if bm & bit] or ["<none>"]

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def rule(title):
    return "="*10 + " " + title + " " + "="*10
