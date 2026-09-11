"""Honest, regression-catching tests for MAVLink-over-RF transport.

Same philosophy as test_rf_receiver: many independent trials under the SAME
impairments, assert a SUCCESS RATE above an honest floor, and on every success
assert the recovered MAVLink fields EXACTLY.

These tests do NOT pin the wire protocol version, so they exercise the deployed
MAVLink2 frames (pwnuav/__init__.py sets MAVLINK20=1). Measured rates over 200
seeds with the clipped detector: telemetry ~0.91, command ~0.99.
"""
import numpy as np

from pymavlink import mavutil

from pwnuav.rf.channel import add_awgn, apply_cfo, prepend_noise
from pwnuav.rf.gfsk import FS
from pwnuav.rf.transport import iq_to_messages, message_to_iq

N_TRIALS = 50
MIN_RATE = 0.80


def _mav():
    return mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)


def _impair(iq, rng, cfo_hz, snr_db):
    offset = int(rng.integers(50, 250))
    ch = prepend_noise(iq, nsamples=offset, rng=rng)
    ch = apply_cfo(ch, f0=cfo_hz, fs=FS)
    ch = add_awgn(ch, snr_db=snr_db, rng=rng)
    return ch


def test_transport_telemetry_success_rate():
    master = np.random.default_rng(0)
    seeds = master.integers(0, 2**31, size=N_TRIALS)

    successes = 0
    for s in seeds:
        rng = np.random.default_rng(int(s))
        mav = _mav()
        msg = mav.global_position_int_encode(
            0, 377749000, -1224194000, 100000, 50000, 0, 0, 0, 0)
        ch = _impair(message_to_iq(mav, msg), rng, cfo_hz=1_200, snr_db=16)
        msgs = iq_to_messages(_mav(), ch)
        hits = [m for m in msgs if m.get_type() == "GLOBAL_POSITION_INT"]
        if hits:
            # on a successful decode, fields must be exact
            assert all(m.lat == 377749000 and m.lon == -1224194000
                       and m.alt == 100000 for m in hits)
            successes += 1

    rate = successes / N_TRIALS
    assert rate >= MIN_RATE, f"telemetry success rate {rate:.2f} < {MIN_RATE}"


def test_transport_injected_command_success_rate():
    master = np.random.default_rng(7)
    seeds = master.integers(0, 2**31, size=N_TRIALS)

    successes = 0
    for s in seeds:
        rng = np.random.default_rng(int(s))
        mav = _mav()
        msg = mav.command_long_encode(
            1, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1, 0, 0, 0, 0, 0, 0)
        ch = _impair(message_to_iq(mav, msg), rng, cfo_hz=1_000, snr_db=20)
        cmds = [m for m in iq_to_messages(_mav(), ch)
                if m.get_type() == "COMMAND_LONG"]
        if cmds:
            assert all(c.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM
                       and c.param1 == 1 for c in cmds)
            successes += 1

    rate = successes / N_TRIALS
    assert rate >= MIN_RATE, f"command success rate {rate:.2f} < {MIN_RATE}"
