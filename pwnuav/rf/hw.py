"""Hardware helpers for the PWNUAV over-the-air demos (tested configuration).

Documented bring-up finding: the HackRF corrupts our GFSK when transmitting;
the ADALM-Pluto transmits it cleanly. That's why the TRANSMITTER (the drone's
radio, or the attacker's uplink) is the Pluto, and the RECEIVER (eavesdropper)
is the RTL-SDR. Also: the RX bandwidth must be set wide (~400 kHz) or the
deviation gets clipped, and the TX must emit a large, continuous buffer, not
small bursts.

TRANSMIT ONLY inside a Faraday cage or cabled with attenuators.
"""
from __future__ import annotations

import time, threading

import numpy as np

from pwnuav.rf.gfsk import FS

try:
    import SoapySDR
    from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_RX, SOAPY_SDR_TX
    HAVE_SOAPY = True
except Exception:  # pragma: no cover
    HAVE_SOAPY = False

_NO_SOAPY = "SoapySDR not installed; use the radio venv (.venv-radio)."
_OPEN_LOCK = threading.Lock()


def _find(driver: str):
    for d in SoapySDR.Device.enumerate():
        if dict(d).get("driver") == driver:
            return d
    return None


def open_tx(driver="plutosdr", freq=915e6, fs=FS, gain=-10, bw=400e3):
    """Open a transmitter (Pluto by default). gain: on the Pluto this is attenuation (0=max)."""
    if not HAVE_SOAPY:
        raise RuntimeError(_NO_SOAPY)
    with _OPEN_LOCK:
        args = _find(driver)
        if args is None:
            raise RuntimeError(f"TX radio driver={driver!r} not found")
        d = SoapySDR.Device(args)
    d.setSampleRate(SOAPY_SDR_TX, 0, fs)
    d.setFrequency(SOAPY_SDR_TX, 0, freq)
    try:
        d.setBandwidth(SOAPY_SDR_TX, 0, bw)
    except Exception:
        pass
    try:
        d.setGain(SOAPY_SDR_TX, 0, gain)
    except Exception:
        pass
    st = d.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
    d.activateStream(st)
    return d, st


def transmit(d, st, iqbuf: np.ndarray, seconds: float) -> None:
    """Transmit iqbuf in a continuous loop for `seconds`, in MTU-sized chunks."""
    mtu = d.getStreamMTU(st)
    iqbuf = iqbuf.astype(np.complex64)
    t0 = time.time()
    while time.time() - t0 < seconds:
        i = 0
        while i < len(iqbuf):
            n = min(mtu, len(iqbuf) - i)
            r = d.writeStream(st, [iqbuf[i:i + n]], n, timeoutUs=300000)
            if r.ret > 0:
                i += r.ret
            elif r.ret < 0:
                break


def open_rx(driver="rtlsdr", freq=915e6, fs=FS, gain=40, bw=400e3):
    """Open a receiver (RTL-SDR by default)."""
    if not HAVE_SOAPY:
        raise RuntimeError(_NO_SOAPY)
    with _OPEN_LOCK:
        args = _find(driver)
        if args is None:
            raise RuntimeError(f"RX radio driver={driver!r} not found")
        d = SoapySDR.Device(args)
    d.setSampleRate(SOAPY_SDR_RX, 0, fs)
    d.setFrequency(SOAPY_SDR_RX, 0, freq)
    try:
        d.setBandwidth(SOAPY_SDR_RX, 0, bw)
    except Exception:
        pass
    try:
        d.setGain(SOAPY_SDR_RX, 0, gain)
    except Exception:
        pass
    st = d.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    d.activateStream(st)
    return d, st


def capture(d, st, seconds: float, fs=FS) -> np.ndarray:
    buf = np.empty(int(fs) // 10, np.complex64)
    out = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        sr = d.readStream(st, [buf], len(buf), timeoutUs=300000)
        if sr.ret > 0:
            out.append(buf[:sr.ret].copy())
    return np.concatenate(out) if out else np.zeros(0, np.complex64)


def close(d, st) -> None:
    try:
        d.deactivateStream(st)
        d.closeStream(st)
    except Exception:
        pass


def decode_messages(samples: np.ndarray, frame_iq_len: int):
    """Slide frame-sized windows over the capture and return MAVLink messages."""
    from pymavlink import mavutil
    from pwnuav.rf.transport import iq_to_messages
    win = frame_iq_len + 20
    step = max(1, win // 3)
    msgs = []
    for i in range(0, max(1, len(samples) - win), step):
        msgs.extend(iq_to_messages(mavutil.mavlink.MAVLink(None), samples[i:i + win]))
    return msgs
