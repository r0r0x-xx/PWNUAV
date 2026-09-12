# rf-bridge — MAVLink over GFSK (PWNUAV)

Carries the emulator's MAVLink from UDP onto real RF. The HackRF is the drone's
radio (TX); the Pluto is the attacker's radio (RX/TX). The modem is a simplified
GFSK (no FHSS, no FEC), enough for recon, eavesdropping and over-the-air injection.

## Link parameters
- Sample rate: 1 Msps · Baud: 100 kbps · SPS: 10 · Deviation: 25 kHz · BT: 0.5
- Carrier: 915 MHz (Americas band)
- Frame: PREAMBLE(0x55 x8) + SYNC(0x2dd4) + len(1) + payload(<=255) + CRC16-CCITT(2)

## Layers (all under pwnuav/rf/)
- framing.py — framing and CRC (tested)
- gfsk.py — GFSK modem over numpy (loopback tested)
- modem.py — MAVLink bytes <-> IQ end-to-end (loopback tested)
- soapy_io.py — SoapySDR HackRF/Pluto adapters (hardware; guarded import)

## Software loopback (no radios)
```python
from pwnuav.rf.modem import encode, decode
iq = encode(b"hello")
assert decode(iq) == [b"hello"]
```

## Real-RF loopback (in a Faraday cage / cabled with attenuators)
Requires SoapySDR + SoapyHackRF + SoapyPlutoSDR.
```bash
python pwnuav/emulator/rf-bridge/rf_loopback.py
```

**Note:** This script is an integration scaffold, not a functional test. The `decode` receiver currently assumes frame-aligned IQ (software loopback). Over real radios you need preamble-correlation timing recovery, CFO/DC removal and TX/RX robustness.

⚠️ Transmit ONLY inside the cage or over a cable with attenuators. Never over-the-air.

## How the PoCs connect to RF (next step)
PoCs 01-03 currently talk over UDP against the stub/SITL. Over RF, the same
MAVLink flow is serialized with pymavlink, passed through `modem.encode` to the
drone's TX (HackRF), and the attacker (Pluto) captures it, runs `modem.decode`
and `mav.decode`. Full PoC-over-RF integration and PoCs 04-05 (GPS spoofing,
jamming) are the next step over real radios.

## Known limitation (v1)
A single frame carries up to 255 bytes of payload. The largest unsigned MAVLink v2 frame is ~265 bytes (10 header + 253 payload + 2 CRC), which exceeds this 255-byte cap; however, the PoC messages (heartbeat, sys_status, global_position_int, attitude, command_long) are well below it. Fragmentation (as SiK does) is left for a later version.
