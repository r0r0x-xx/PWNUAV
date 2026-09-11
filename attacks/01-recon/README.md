# PoC 01 — MAVLink recon (over-the-air)

**PWNUAV stages:** RC-01 (band ID) · RC-02 (heartbeat/fingerprint) · RC-03 (system enumeration) · PA-02 (message-ID mapping)
**Mode:** RF / over-the-air (Faraday cage) · **venv:** `.venv-radio`

## What it demonstrates
With no authentication and no prior knowledge, the attacker discovers the drone by listening only: it characterizes the link, inventories the MAVLink messages in flight, and enumerates the vehicle (sysid, type, autopilot, modes).

## How it works
1. The emulated drone emits its telemetry cycle (HEARTBEAT, SYS_STATUS, GPS_RAW_INT, GLOBAL_POSITION_INT, ATTITUDE, VFR_HUD).
2. It is modulated to IQ (GFSK 915 MHz) and transmitted continuously by the **Pluto**.
3. The **RTL-SDR** captures ~2 s; `receiver.receive` demodulates and pymavlink parses.
4. It builds: (RC-02) the link fingerprint, (PA-02) an inventory by MSGID/name/count, (RC-03) vehicle enumeration with enum names and `base_mode` flags, and a hexdump of the raw HEARTBEAT (MAVLink 2 frame, `0xFD`).

## Command (input)
```
$ python attacks/01-recon/recon_aire.py
```

## Real output
```
========== PWNUAV RECON — MAVLink over the air ==========
[*] SDR RX     : RTL-SDR @ 915.000 MHz  fs=1.0 Msps  gain=40 dB
[*] Victim link: Pluto TX  GFSK 100 kbps  dev 25 kHz  (drone downlink)
[*] Capturing 2.0 s of spectrum ...
[*] Captured 2,066,080 IQ samples ; 84 MAVLink frames recovered

[RC-02] LINK FINGERPRINT
  modulation : GFSK  BT=0.5  h=0.5
  framing    : PREAMBLE(0x55 x8) + SYNC(0x2D D4) + MAVLink2 + CRC-16
  carrier    : 915.000 MHz   frames/2s : 84

[PA-02] MAVLINK MESSAGE INVENTORY
  MSGID  NAME                        COUNT
  0      HEARTBEAT                   37
  1      SYS_STATUS                  4
  24     GPS_RAW_INT                 3
  30     ATTITUDE                    13
  33     GLOBAL_POSITION_INT         9
  74     VFR_HUD                     18

[RC-03] VEHICLE ENUMERATION
  system id      : 1
  component id   : 1  (MAV_COMP_ID_AUTOPILOT1)
  vehicle type   : 2  MAV_TYPE_QUADROTOR
  autopilot      : 3  MAV_AUTOPILOT_ARDUPILOTMEGA
  base_mode      : 0x01  [CUSTOM_MODE]
  custom_mode    : 4
  system_status  : 4  MAV_STATE_ACTIVE
  mavlink version: 3

[*] SAMPLE HEARTBEAT — raw MAVLink 2 frame on the air
  0000  FD 09 00 00 00 01 01 00 00 00 04 00 00 00 02 03   ................
  0010  01 04 03 6D 7B                                    ...m{

[+] RECON COMPLETE — 1 vehicle fingerprinted with ZERO authentication.
```

## Interpretation
- **Inventory (PA-02):** every observed MSGID with its count — the attacker maps which messages the system uses without any documentation.
- **Enumeration (RC-03):** type=QUADROTOR, autopilot=ARDUPILOTMEGA, status=ACTIVE, MAVLink version 3, all derived from the HEARTBEATs.
- **Hexdump:** the real v2 frame over the air (`0xFD` STX). All of it is achieved **by listening only**.

## Safety
Pure RX on the attacker side, but the drone transmits: ONLY in a Faraday cage.
