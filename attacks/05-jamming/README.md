# PoC 05 — Jamming / DoS of the link (over-the-air)

**PWNUAV stages:** IM-01 (RF/protocol jamming & DoS) · IM-02 (failsafe trigger)
**Mode:** RF / over-the-air · **venv:** `.venv-radio`

## What it demonstrates
Band-limited noise on 915 MHz denies the telemetry link: decoding drops ~90-99%. On a real drone, that sustained loss trips the failsafe (RTL / LAND).

## How it works
1. **Baseline phase:** the drone (Pluto) transmits; the RTL-SDR counts decoded heartbeats.
2. **Jammed phase:** in parallel, the **HackRF** transmits gaussian noise **concentrated in ±120 kHz** (the bandwidth occupied by the GFSK) at maximum gain; the drone keeps transmitting.
3. The rates and % loss are compared.

> Technical key: all radios are opened before capturing (so both TXs are active during the window), and the noise is filtered to ±120 kHz to concentrate power in the signal band. Wideband noise (1 MHz) wastes power. The jammer decodes nothing: any radio works (which is why the HackRF, though not a faithful GFSK TX, works as a jammer).

## Command (input)
```
$ python attacks/05-jamming/jam_aire.py
```

## Real output
```
========== PWNUAV JAMMING / DoS — 915 MHz link ==========
[*] Victim : Pluto TX MAVLink @ 915 MHz   Monitor : RTL-SDR RX

[BASELINE] no jammer, 1.5s
   frames decoded :  449   rate ~ 299.3/s   packet loss 0%

[*] Jammer: HackRF, band-limited AWGN +/-120 kHz, TX gain 47 (max)
    (all jammer power concentrated in the ~150 kHz occupied by the GFSK)

[JAMMED] jammer ON, 1.5s
   frames decoded :   42   rate ~  28.0/s   packet loss 90.6%

[IM-01] Link denied: 449 -> 42 heartbeats (90.6% loss).
[IM-02] Sustained loss exceeds the GCS failsafe timeout -> RTL / LAND.
[+] PoC 05 jamming OVER-THE-AIR: OK
```

## Interpretation
- **Baseline:** healthy link (~450 heartbeats in 1.5 s).
- **Jammed:** collapses ~90-99% (effective DoS, IM-01).
- On a real link, that loss beats the GCS timeout → failsafe/RTL (IM-02).

## Safety
Jamming is illegal over the air and affects third parties. ONLY in a Faraday cage or cable with attenuators.
