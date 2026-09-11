# ArduPilot SITL - PWNUAV integration target

The `DroneStub` covers the tests. For high-fidelity demos we use ArduPilot SITL
(ArduCopter), which speaks real MAVLink.

## Installation on macOS (Apple Silicon)
```bash
brew install gcc pkg-config
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
python3 -m pip install -r Tools/environment_install/requirements.txt || true
./waf configure --board sitl
./waf copter
```
If the native build fails, use the Docker/Linux VM fallback (see the section below).

## Running
```bash
cd ardupilot
Tools/autotest/sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550 --no-mavproxy
```
SITL transmits ("--out") to 127.0.0.1:14550. The PoCs connect with a binding
endpoint:
```bash
pwnuav-recon     --connect udpin:127.0.0.1:14550 --duration 3
pwnuav-eavesdrop --connect udpin:127.0.0.1:14550 --duration 3
pwnuav-inject    --connect udpin:127.0.0.1:14550 --mode 4
```

## Docker/Linux VM fallback
```bash
docker run --rm -it radarku/ardupilot-sitl \
  sim_vehicle.py -v ArduCopter --out=udp:HOST_IP:14550 --no-mavproxy
```
Replace HOST_IP with the host machine's IP (the gateway as seen from the container).
The PoCs connect with a binding endpoint:
```bash
pwnuav-recon     --connect udpin:0.0.0.0:14550 --duration 3
pwnuav-eavesdrop --connect udpin:0.0.0.0:14550 --duration 3
pwnuav-inject    --connect udpin:0.0.0.0:14550 --mode 4
```

## Vulnerable-by-design config
In the MAVProxy/QGC console, leave MAVLink2 signing disabled (it is by default)
to reflect the assessment scenario.
