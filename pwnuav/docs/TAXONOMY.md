# PWNUAV Matrix — a TTP taxonomy for drones

> **Why it exists.** For satellites there is **SPARTA** (The Aerospace Corporation):
> a consolidated matrix of offensive tactics and techniques. For drones there is **no
> consolidated equivalent**. That gap is part of the argument for this project, and the PWNUAV
> Matrix is the proposal to fill it: 7 stages (tactics) with their own TTPs, mapped
> one-to-one onto the 5-phase red-team methodology.

## Relationship to the 5-phase methodology

| Phase (methodology) | PWNUAV stages |
|---|---|
| 1. RF recon | RC |
| 2. Protocol reverse engineering | PA |
| 3. C2 surface analysis | IA, C2 |
| 4. Air-gap crossing via SDR | NV (RF as the bridge into the navigation system) |
| 5. Impact assessment | EX, IM |

## The 7 stages

### RC · RF & Network Reconnaissance
Discover the link, the band and the actors before touching anything.

| ID | Technique | Description |
|---|---|---|
| RC-01 | Spectrum sweep / band ID | Sweep the spectrum to locate the telemetry and video downlink |
| RC-02 | Heartbeat detection & link fingerprint | Detect HEARTBEAT and characterize the link (modulation, rate) |
| RC-03 | System/Component enumeration | Enumerate autopilot type, firmware and components over MAVLink |
| RC-04 | GCS & operator discovery | Locate the ground control station and the operator |

### PA · Protocol Analysis / Reverse Engineering
Turn RF samples into readable MAVLink messages and understand what can be touched.

| ID | Technique | Description |
|---|---|---|
| PA-01 | Demodulation & framing recovery | Demodulate GFSK and recover the link framing (SiK-style) |
| PA-02 | Dialect & message-ID mapping | Map the MAVLink dialect and the message IDs in use |
| PA-03 | Auth/crypto assessment | Assess the presence/absence of MAVLink2 signing and encryption |
| PA-04 | Sequence & timing analysis | Analyze sequence numbers and timing for injection/replay |

### IA · Link Access
Gain a position over the link (passive or active).

| ID | Technique | Description |
|---|---|---|
| IA-01 | Passive tap / promiscuous capture | Passively capture all link traffic |
| IA-02 | Man-in-the-middle | Interpose on the RF/serial/UDP link |
| IA-03 | Rogue node / injection point | Introduce a node or injection point on the bus |
| IA-04 | Weak/no pairing exploitation | Abuse weak or absent pairing |

### C2 · GCS Impersonation
Pass yourself off as the legitimate ground control station.

| ID | Technique | Description |
|---|---|---|
| C2-01 | GCS spoofing / identity impersonation | Spoof the system/component ID of the GCS |
| C2-02 | Heartbeat & sequence synchronization | Sync HEARTBEAT and sequence so the traffic is not rejected |
| C2-03 | Channel takeover | Out-shout the legitimate GCS and take the channel |
| C2-04 | Failsafe / telemetry suppression | Suppress telemetry or failsafe to hide the attack |

### EX · Command Injection / Execution
Execute commands on the drone.

| ID | Technique | Description |
|---|---|---|
| EX-01 | Mode change injection | Force a flight-mode change (GUIDED/LAND/RTL) |
| EX-02 | Arm/Disarm injection | Arm or disarm the motors |
| EX-03 | Waypoint / mission rewrite | Rewrite waypoints or the mission |
| EX-04 | Parameter tampering | Alter parameters via PARAM_SET |
| EX-05 | Command replay | Replay captured commands |

### NV · Navigation & Sensor Manipulation
Manipulate the drone's perception of the world (the air-gap crossing through sensors).

| ID | Technique | Description |
|---|---|---|
| NV-01 | GPS spoofing | Inject fake GPS position/time over RF |
| NV-02 | EKF / sensor poisoning | Poison the state estimator or the sensors |
| NV-03 | Geofence bypass | Evade or relocate the geofence |
| NV-04 | Home-point manipulation | Manipulate the return-to-home point |

### IM · Impact / Effects
The final, measurable effect.

| ID | Technique | Description |
|---|---|---|
| IM-01 | RF/protocol jamming & DoS | Deny the link through noise or flooding |
| IM-02 | Failsafe trigger | Trigger a failsafe (RTL/LAND/fly-away) |
| IM-03 | Trajectory hijack | Hijack the vehicle's trajectory |
| IM-04 | Telemetry exfiltration | Exfiltrate telemetry (confidentiality) |
| IM-05 | Physical loss of vehicle | Physical loss / crash of the vehicle |

## Mapping the 5 PoCs onto the matrix

| PoC | TTPs covered |
|---|---|
| 01 Recon MAVLink | RC-01, RC-02, RC-03, PA-02 |
| 02 Telemetry eavesdropping | IA-01, PA-01, IM-04 |
| 03 Command injection | C2-01, C2-02, EX-01, EX-02, EX-03, EX-05 |
| 04 GPS spoofing | NV-01, IM-02, IM-03 |
| 05 Jamming / DoS | IM-01, IM-02 |
