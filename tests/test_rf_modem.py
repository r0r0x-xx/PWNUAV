from pymavlink import mavutil

from pwnuav.rf.modem import encode, decode


def test_modem_payload_roundtrip():
    payload = b"PWNUAV over the air \x00\x01\x02"
    frames = decode(encode(payload))
    assert frames == [payload]


def test_modem_carries_mavlink_heartbeat():
    mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    msg = mav.heartbeat_encode(
        mavutil.mavlink.MAV_TYPE_QUADROTOR,
        mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
        0, 0, mavutil.mavlink.MAV_STATE_ACTIVE,
    )
    buf = msg.pack(mav)
    frames = decode(encode(buf))
    assert frames == [buf]
    # the recovered bytes parse back to a HEARTBEAT
    parsed = mav.decode(bytearray(frames[0]))
    assert parsed.get_type() == "HEARTBEAT"
    assert parsed.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA
