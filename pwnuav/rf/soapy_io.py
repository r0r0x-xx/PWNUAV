"""SoapySDR I/O adapters for the PWNUAV RF bridge.

SdrSink transmits IQ on the HackRF (the drone's radio); SdrSource receives IQ
on the ADALM-Pluto (the attacker's radio). SoapySDR is an OPTIONAL dependency:
this module imports cleanly without it, and only instantiating an adapter
requires it. Transmit only inside a Faraday cage / cabled with attenuators.
"""
from __future__ import annotations

import numpy as np

from pwnuav.rf.gfsk import FS

try:
    import SoapySDR
    from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_RX, SOAPY_SDR_TX
    HAVE_SOAPY = True
except Exception:  # pragma: no cover - exercised only without SoapySDR
    HAVE_SOAPY = False

_NO_SOAPY = (
    "SoapySDR is not installed. Install SoapySDR plus the device support "
    "(SoapyHackRF, SoapyPlutoSDR) to drive real radios."
)


def _open_device(driver: str):
    """Open a SoapySDR device by driver name using its FULL enumeration args.

    Opening with just ``{"driver": driver}`` works for the HackRF but FAILS on
    real ADALM-Pluto hardware ("SoapySDR::Device::make() no match") because the
    Pluto needs its full enumeration args (e.g. a ``uri`` like ``usb:0.1.5``).
    Enumerate, pick the first entry matching the driver, and open with those.
    """
    for args in SoapySDR.Device.enumerate():
        if dict(args).get("driver") == driver:
            return SoapySDR.Device(args)
    raise RuntimeError(
        f"no SoapySDR device with driver={driver!r} found (is it connected?)")


class SdrSink:
    """Transmit IQ on the drone radio (default HackRF)."""

    def __init__(self, freq: float = 915e6, fs: float = FS, gain: float = 20,
                 driver: str = "hackrf"):
        if not HAVE_SOAPY:
            raise RuntimeError(_NO_SOAPY)
        self.dev = _open_device(driver)
        self.dev.setSampleRate(SOAPY_SDR_TX, 0, fs)
        self.dev.setFrequency(SOAPY_SDR_TX, 0, freq)
        self.dev.setGain(SOAPY_SDR_TX, 0, gain)
        self.stream = self.dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
        self.dev.activateStream(self.stream)

    def send(self, iq: np.ndarray) -> None:
        self.dev.writeStream(self.stream, [iq.astype(np.complex64)], len(iq))

    def close(self) -> None:
        self.dev.deactivateStream(self.stream)
        self.dev.closeStream(self.stream)


class SdrSource:
    """Receive IQ on the attacker radio (default ADALM-Pluto)."""

    def __init__(self, freq: float = 915e6, fs: float = FS, gain: float = 30,
                 driver: str = "plutosdr"):
        if not HAVE_SOAPY:
            raise RuntimeError(_NO_SOAPY)
        self.dev = _open_device(driver)
        self.dev.setSampleRate(SOAPY_SDR_RX, 0, fs)
        self.dev.setFrequency(SOAPY_SDR_RX, 0, freq)
        self.dev.setGain(SOAPY_SDR_RX, 0, gain)
        self.stream = self.dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.dev.activateStream(self.stream)

    def recv(self, n: int) -> np.ndarray:
        buf = np.empty(n, dtype=np.complex64)
        got = 0
        while got < n:
            chunk = np.empty(n - got, dtype=np.complex64)
            sr = self.dev.readStream(self.stream, [chunk], n - got)
            if sr.ret > 0:
                buf[got:got + sr.ret] = chunk[:sr.ret]
                got += sr.ret
        return buf

    def close(self) -> None:
        self.dev.deactivateStream(self.stream)
        self.dev.closeStream(self.stream)
