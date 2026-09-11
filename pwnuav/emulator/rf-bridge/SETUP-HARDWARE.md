# Hardware setup and validated over-the-air configuration

Radios used: **HackRF One**, **ADALM-Pluto**, **RTL-SDR Blog V4**. All TX is done
ONLY inside the Faraday cage or cabled with attenuators.

## Key bring-up finding
The **HackRF corrupts the GFSK waveform when transmitting** our modulation (it
reproduces a clean tone, but not the modulated signal beyond the start of the
burst). Confirmed by isolating a single variable: two different receivers (Pluto
and RTL) saw the same decorrelation with the HackRF transmitting. The **Pluto
transmits clean**. In addition, the RX bandwidth must be fixed at ~400 kHz or the
deviation gets clipped, and the TX must emit a large, continuous buffer.

## Validated radio roles
| Function | Radio |
|---|---|
| Drone / attacker uplink (GFSK TX) | **ADALM-Pluto** (clean) |
| Eavesdropper / receiver (RX) | **RTL-SDR** (or Pluto) |
| Jammer (noise TX, no fidelity required) | **HackRF** |

These roles live in `pwnuav/rf/hw.py` (open_tx=plutosdr, open_rx=rtlsdr by default).

## Installation (macOS, Apple Silicon)
The HackRF comes ready with `brew install hackrf soapyhackrf soapysdr`. The Pluto
was built from source (there is no Homebrew formula):

```bash
brew install cmake libusb libxml2 flex bison
# libiio 0.25 as a dylib (NOT a framework); CMake 4.x needs the policy flag
git clone https://github.com/analogdevicesinc/libiio.git && cd libiio && git checkout v0.25
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/opt/homebrew -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DHAVE_DNS_SD=OFF -DWITH_TESTS=OFF -DWITH_DOC=OFF -DWITH_EXAMPLES=OFF -DOSX_FRAMEWORK=OFF ..
make -j && make install && cd ../..
# SoapyPlutoSDR (pothosware, NOT analogdevicesinc); libad9361 is optional -> skip
git clone https://github.com/pothosware/SoapyPlutoSDR.git && cd SoapyPlutoSDR
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/opt/homebrew -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
make -j && make install && cd ../..
# GOTCHA: the module links @rpath/libiio.0.dylib with no rpath -> factory "MISSING".
install_name_tool -change @rpath/libiio.0.dylib /opt/homebrew/lib/libiio.0.dylib \
  /opt/homebrew/lib/SoapySDR/modules0.8/libPlutoSDRSupport.so
SoapySDRUtil --find     # should list hackrf, plutosdr and rtlsdr
```

## Radio Python environment
The SoapySDR binding lives in Homebrew's Python, not in the conda venv:

```bash
cd <repo-root>
/opt/homebrew/bin/python3 -m venv --system-site-packages .venv-radio
source .venv-radio/bin/activate
pip install -e "<repo-root>/PWNUAV[dev]"
python -c "import SoapySDR, numpy, pymavlink, pwnuav; print('OK')"
```

## Over-the-air validation results (in the cage)
| PoC | Mode | Result |
|---|---|---|
| 01 Recon | over-the-air (Pluto TX / RTL RX) | OK — 301 HEARTBEAT, drone sysid=1 QUADROTOR ARDUPILOTMEGA |
| 02 Eavesdrop | over-the-air | OK — position 37.7749,-122.4194 / yaw 1.57 / battery 12.0V 75% |
| 03 Command injection | over-the-air (Pluto TX attacker / RTL RX) | OK — ARM param1=1 from fake GCS 255, x151 |
| 04 GPS spoofing | local/virtual (GPS_INPUT) | OK — position spoofed to 6.2518,-75.5636 |
| 05 Jamming | over-the-air (HackRF noise) | OK — link 211 -> 0 HEARTBEAT with jammer |

## How to run the demos (radio venv, in the cage)
```bash
source <repo-root>/.venv-radio/bin/activate
python attacks/01-recon/recon_aire.py
python attacks/02-eavesdrop/eavesdrop_aire.py
python attacks/03-cmd-injection/inject_aire.py
python attacks/05-jamming/jam_aire.py
# GPS is local (normal venv .venv):
python attacks/04-gps-spoof/gps_spoof_local.py
```
