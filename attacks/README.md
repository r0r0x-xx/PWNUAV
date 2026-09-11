# PWNUAV — Attack demos (PoCs)

Five PoCs that apply the offensive methodology to a vulnerable-by-design MAVLink drone.
Four run **over-the-air** with SDRs in a Faraday cage; GPS spoofing is **local/virtual**.

## Radio setup (validated)
| Function | Radio |
|---|---|
| Drone / attacker uplink (GFSK TX) | ADALM-Pluto |
| Eavesdropper / receiver (RX) | RTL-SDR |
| Jammer (noise TX) | HackRF |

Details and installation: `../pwnuav/emulator/rf-bridge/SETUP-HARDWARE.md`.
Finding: the HackRF corrupts the GFSK when transmitting; the Pluto transmits clean.

## Results
| PoC | PWNUAV stage | Mode | Command | Result |
|---|---|---|---|---|
| 01 Recon | RC/PA | RF | `python attacks/01-recon/recon_aire.py` | drone enumerated (sysid=1 QUADROTOR ArduPilot) + message inventory |
| 02 Eavesdrop | IA-01/IM-04 | RF | `python attacks/02-eavesdrop/eavesdrop_aire.py` | full flight picture in the clear (pos/GPS/attitude/battery) |
| 03 Injection | C2/EX-01-02 | RF | `python attacks/03-cmd-injection/inject_aire.py` | valid ARM + SET_GUIDED over-the-air from a spoofed GCS (255) |
| 04 GPS spoof | NV-01/IM-03 | Local | `python attacks/04-gps-spoof/gps_spoof_local.py` | position jumped ~5,876 km to forged coordinates |
| 05 Jamming | IM-01/IM-02 | RF | `python attacks/05-jamming/jam_aire.py` | link ~449 -> ~42 heartbeats (~90% loss, DoS) |

## How to run
```bash
# Over-the-air PoCs (cage): radio environment
source .venv-radio/bin/activate    # (at the repo root)
python attacks/01-recon/recon_aire.py
python attacks/02-eavesdrop/eavesdrop_aire.py
python attacks/03-cmd-injection/inject_aire.py
python attacks/05-jamming/jam_aire.py

# GPS spoofing (local): normal environment
source .venv/bin/activate
python attacks/04-gps-spoof/gps_spoof_local.py
```

## Layout of each folder
- `README.md` — what it demonstrates, how it works, command (input), real output, interpretation, safety.
- `*_aire.py` / `gps_spoof_local.py` — the attack script.
- `output.txt` — real captured output from the run (verbose: dissection, tables, hex).

Full taxonomy: `../pwnuav/docs/TAXONOMY.md`.
