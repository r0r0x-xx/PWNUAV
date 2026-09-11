from pymavlink import mavutil

from pwnuav.recon import run_recon


def test_recon_finds_vehicle(drone):
    _, conn = drone
    result = run_recon(conn, duration=3.0)
    assert result.heard is True
    assert result.system_id == 1
    assert result.vehicle_type == mavutil.mavlink.MAV_TYPE_QUADROTOR
    assert result.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA


def test_recon_observes_telemetry_message_ids(drone):
    _, conn = drone
    result = run_recon(conn, duration=3.0)
    assert mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT in result.message_ids
    assert (mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT
            in result.message_ids)
