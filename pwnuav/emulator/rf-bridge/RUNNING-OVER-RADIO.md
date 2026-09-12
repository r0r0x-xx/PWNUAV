# Running the PoCs over the air (HackRF + Pluto, in the cage)

The lab is virtual (SITL/stub + software modem). These PoCs run over the air on
the 915 MHz link; GPS spoofing (PoC 04) is virtual (see its runbook).

## Setup
- Drone side: emulator (SITL or DroneStub) -> `pwnuav/emulator/rf-bridge/drone_tx.py` -> HackRF TX 915 MHz.
- Attacker side: `pwnuav/emulator/rf-bridge/attacker_rf.py` -> Pluto RX/TX.
- Everything inside the Faraday cage.

## PoCs
- 01 Recon:        `python pwnuav/emulator/rf-bridge/attacker_rf.py recon`      (RC/PA)
- 02 Eavesdrop:    `python pwnuav/emulator/rf-bridge/attacker_rf.py eavesdrop`  (IA-01/IM-04)
- 03 Injection:    `python pwnuav/emulator/rf-bridge/attacker_rf.py inject`     (C2/EX)
- 04 GPS spoofing: VIRTUAL (not over the air) -> `pwnuav/gps_spoof.py --connect udpin:127.0.0.1:14550` (NV-01/IM-03)
- 05 Jamming:      `python attacks/05-jamming/jam.py`                       (IM-01/IM-02)

The MAVLink logic is the same as over UDP; only the transport changes to RF via
`pwnuav.rf.transport` (validated in software by `tests/test_rf_transport.py`).

## Safety
All transmission ONLY in a Faraday cage or cabled with attenuators.
