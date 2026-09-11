# PWNUAV — Technical design

Talk: "Orbital Red Teaming" · Author: Romel Marin (r0r0x)

## Goal
A vulnerable-by-design MAVLink drone emulator with 5 attack PoCs that mirror the
5-phase red-team methodology of the talk and validate the PWNUAV Matrix taxonomy.

## Design decisions
- **Autopilot:** ArduPilot (SITL).
- **Environment:** macOS. SDR stack via radioconda (GNU Radio + gr-osmosdr + SoapySDR).
  Docker/Linux VM as a fallback if the native SITL build misbehaves on Apple Silicon.
- **Drone radio:** HackRF One, transmitting the telemetry downlink (half-duplex).
- **Attacker radio:** ADALM-Pluto, full-duplex (RX+TX).
- **RF layer:** transmit ONLY inside a Faraday cage, at minimum power. Demos are recorded.

## Architecture

```
            FARADAY CAGE
  +-------------------------------------------------+
  |                                                 |
  |  [ArduPilot SITL] --MAVLink(UDP)--> [rf-bridge] |
  |    (drone brain)                        |       |
  |                                    HackRF TX    |
  |                                    (GFSK 915MHz) |
  |                                         )))     |
  |                                          |      |
  |                                    Pluto RX/TX  |
  |                                    [ATTACKER]   |
  |                                                 |
  |  GPS spoof: virtual GPS_INPUT injection via pwnuav/gps_spoof.py |
  +-------------------------------------------------+
```

### Components
1. **pwnuav/emulator/sitl/** — ArduPilot SITL (ArduCopter) bootstrap. Configured
   vulnerable-by-design: MAVLink2 **unsigned**, no encryption, default failsafes.
   Exposes MAVLink over local UDP.
2. **pwnuav/emulator/rf-bridge/** — takes the SITL MAVLink stream and modulates it as
   GFSK to transmit over the HackRF at 915 MHz (emulates a SiK-style link, simplified:
   no FHSS, no FEC). **[implemented v1]** GFSK modem in `pwnuav/rf/` (framing + gfsk +
   modem), verified by software loopback; SoapySDR I/O for HackRF/Pluto is documented.
   v1 limitation: 255-byte payload per frame (no fragmentation). The attacker (Pluto)
   demodulates the same link.
3. **attacks/** — one directory per PoC, with the attack script, a demo walkthrough and
   the mapping to TTPs.

### RF and PoC implementation
- **[implemented]** RF receiver `pwnuav/rf/receiver.py` (preamble correlation + CFO/DC
  correction) and transport `pwnuav/rf/transport.py` (MAVLink-over-RF), tested against a
  channel model.
- **Over-the-air PoCs** (recon/eavesdrop/injection/jamming) via `pwnuav/emulator/rf-bridge/`
  and `attacks/05-jamming/`, run inside the cage. **PoC 04 GPS spoofing is virtual**,
  performed by GPS_INPUT injection (`pwnuav/gps_spoof.py`), with no GPS hardware.

### Data flow per PoC
- **01 Recon / 02 Eavesdrop:** Pluto RX -> GFSK demod -> pymavlink parses -> HEARTBEAT,
  SYS_STATUS, GLOBAL_POSITION_INT and ATTITUDE are listed.
- **03 Command injection:** Pluto synchronizes the sequence (PA-04) and transmits a
  MAVLink command (COMMAND_LONG: MAV_CMD_DO_SET_MODE / MAV_CMD_COMPONENT_ARM_DISARM /
  MISSION_ITEM). It requires the drone in RX; the HackRF half-duplex timing is handled
  (see Risks).
- **04 GPS spoofing (virtual):** `pwnuav/gps_spoof.py` injects a fake GPS_INPUT MAVLink
  message -> the stack adopts the fake position -> GLOBAL_POSITION_INT reflects the jump /
  failsafe. No GPS hardware (no instrumented UART/receiver).
- **05 Jamming:** Pluto TX noise/tone at 915 MHz -> the telemetry link drops -> ArduPilot
  GCS failsafe -> RTL (IM-02).

### Link reliability (measured, honest)
The v1 receiver (`pwnuav/rf/receiver.py`) is NOT perfect and the link has NO FEC, so
**individual frames are lost**:
- The burst detector uses **unnormalized** preamble correlation. The discriminator values
  of the real preamble are only ~±(2·π·DEV/FS) ≈ 0.157 rad/sample, whereas the initial
  noise (`channel.prepend_noise`) spans ±π and can win the `argmax` — the receiver locks
  onto noise and drops the frame, **independent of SNR**.
- Mitigation applied: clip the discriminator to a small multiple of the ideal magnitude
  before correlating. Measured over 200 random seeds with an unaligned initial offset +
  CFO + AWGN, the per-burst success rate rose from **~0.70 (no clip) to ~0.90 (clipped)**.
  There is still ~10% per-burst loss.
- **Real operation: retransmission.** The drone bridge (`drone_tx`) transmits in a loop and
  the attacker inject (`attacker_rf`) repeats, so it recovers across a majority of repeated
  bursts. `receive()` recovers a single burst per call; the caller repeats.
- **MAVLink2 vs 1.0.** The deployed default is MAVLink2 (`pwnuav/__init__.py` sets
  `MAVLINK20=1`). v2 frames are longer than v1, so they recover slightly worse (more samples
  exposed to the channel per frame). The RF tests exercise the deployed v2 frames: they run
  **many trials** with different seeds and assert a **success rate ≥ 0.80** (an honest floor
  below the measured ~0.90 and above the ~0.70 of the unclipped detector, so a regression
  fails), verifying the exact payload on every successful decode.

## Stack / dependencies (macOS)
- radioconda (GNU Radio, gr-osmosdr, SoapySDR, SoapyPlutoSDR)
- hackrf tools (`brew install hackrf`)
- libiio / libad9361 for the Pluto (`brew install libiio libad9361-iio`)
- ArduPilot SITL (build from source or Docker)
- Python: pymavlink, pySerial, numpy
- MAVProxy or QGroundControl as the reference legitimate GCS

## Technical risks and mitigations
1. **HackRF half-duplex vs command injection.** The HackRF cannot TX telemetry and RX
   commands at the same time. Mitigation: in PoC 03 the drone operates in an RX window, or
   the rf-bridge time-multiplexes TX/RX; alternatively the command link is handled by the
   full-duplex Pluto and the HackRF only does the downlink. To be validated in implementation.
2. **GPS spoofing against pure SITL.** SITL simulates its GPS internally; it does not read
   RF. **Decision:** use GPS_INPUT injection over MAVLink (`pwnuav/gps_spoof.py`) so the
   stack adopts a fake position -> observable jump in GLOBAL_POSITION_INT / failsafe (NV-01).
   A GPS-hardware-free approach that avoids the complexity of an instrumented UART/u-blox
   receiver.
3. **Simplified SiK emulation.** The rf-bridge v1 uses GFSK without FHSS/FEC. Enough to
   demonstrate recon/demod/inject; documented as a conscious simplification.
4. **GNU Radio on macOS.** May require radioconda instead of Homebrew. Docker/Linux VM as
   plan B for the full SDR stack.

## Open items
- **[resolved]** GPS PoC 04: virtual GPS_INPUT injection via `pwnuav/gps_spoof.py`.
- Confirm the ISM frequency of the telemetry link (assumed default: 915 MHz, Americas band).
