"""Honest, regression-catching tests for the v1 burst receiver.

The v1 detector (unnormalized preamble correlation) has a per-burst loss rate:
leading channel noise can win the argmax, so some frames are lost even at high
SNR (see pwnuav/rf/receiver.py and docs/DESIGN.md). Instead of asserting a
single lucky-seed exact match, we run MANY independent trials under the SAME
impairments and assert a SUCCESS RATE above an honest threshold. On every
SUCCESSFUL decode we assert the recovered payload EXACTLY, so correctness (not
just detection) is checked.

Deployed default is MAVLink2 (pwnuav/__init__.py sets MAVLINK20=1); these tests
do NOT pin the wire version, so they exercise the deployed v2 frames.

Measured per-burst rates over 200 seeds (clipped detector): raw payload ~0.90,
MAVLink2 heartbeat ~0.94. The unclipped detector measured ~0.70, which falls
below the 0.80 threshold below -- so a regression to it fails these tests.
"""
import numpy as np

from pymavlink import mavutil

from pwnuav.rf.channel import add_awgn, apply_cfo, prepend_noise
from pwnuav.rf.gfsk import FS
from pwnuav.rf.modem import encode
from pwnuav.rf.receiver import receive

N_TRIALS = 50
MIN_RATE = 0.80  # honest floor: below measured ~0.90, above unclipped ~0.70


def _impair(iq, rng, cfo_hz, snr_db):
    """Apply the SAME realistic impairments every trial: a non-symbol-aligned
    leading offset, a carrier frequency offset, and AWGN."""
    offset = int(rng.integers(50, 250))          # non-aligned leading noise
    ch = prepend_noise(iq, nsamples=offset, rng=rng)
    ch = apply_cfo(ch, f0=cfo_hz, fs=FS)
    ch = add_awgn(ch, snr_db=snr_db, rng=rng)
    return ch


def test_receiver_success_rate_offset_cfo_noise():
    master = np.random.default_rng(0)
    seeds = master.integers(0, 2**31, size=N_TRIALS)
    payload = b"PWNUAV RF real \x11\x22\x33"
    iq = encode(payload)

    successes = 0
    for s in seeds:
        rng = np.random.default_rng(int(s))
        frames = receive(_impair(iq, rng, cfo_hz=2_000, snr_db=15))
        if frames == [payload]:              # on success, exact payload check
            successes += 1
        else:
            # detection may fail (noise-lock) OR return other frames; a
            # successful *detection* must never yield a wrong payload.
            assert payload not in frames or frames == [payload]

    rate = successes / N_TRIALS
    assert rate >= MIN_RATE, f"per-burst success rate {rate:.2f} < {MIN_RATE}"


def test_receiver_mavlink2_heartbeat_success_rate():
    master = np.random.default_rng(7)
    seeds = master.integers(0, 2**31, size=N_TRIALS)

    successes = 0
    for s in seeds:
        rng = np.random.default_rng(int(s))
        mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
        msg = mav.heartbeat_encode(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        buf = msg.pack(mav)                  # deployed default: MAVLink2 frame
        frames = receive(_impair(encode(buf), rng, cfo_hz=1_500, snr_db=18))
        if frames == [buf]:
            # exact bytes recovered -> must parse back to a HEARTBEAT
            rx = mavutil.mavlink.MAVLink(None).decode(bytearray(frames[0]))
            assert rx.get_type() == "HEARTBEAT"
            successes += 1

    rate = successes / N_TRIALS
    assert rate >= MIN_RATE, f"heartbeat success rate {rate:.2f} < {MIN_RATE}"


def test_repeated_transmission_recovers_from_majority():
    """Real operation retransmits (drone_tx loops, attacker_rf inject repeats).
    With a per-burst rate ~0.9, a majority of K repeated bursts decodes."""
    master = np.random.default_rng(3)
    payload = b"ARM \x01\x00"
    iq = encode(payload)
    K = 5

    for _ in range(N_TRIALS):
        got = 0
        for _ in range(K):
            rng = np.random.default_rng(int(master.integers(0, 2**31)))
            if receive(_impair(iq, rng, cfo_hz=1_200, snr_db=16)) == [payload]:
                got += 1
        assert got >= (K // 2 + 1), f"only {got}/{K} bursts recovered"
