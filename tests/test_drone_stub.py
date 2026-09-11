from pymavlink import mavutil

from pwnuav.link import connect, announce
from tests._util import wait_until


def test_stub_emits_heartbeat(drone):
    _, conn = drone
    master = connect(conn)
    announce(master)
    hb = master.wait_heartbeat(timeout=5)
    assert hb is not None
    assert hb.get_srcSystem() == 1
    assert hb.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA
    master.close()


def test_stub_records_arm_command(drone):
    stub, conn = drone
    master = connect(conn)
    announce(master)
    master.wait_heartbeat(timeout=5)
    master.mav.command_long_send(
        1, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1, 0, 0, 0, 0, 0, 0,
    )
    assert wait_until(lambda: stub.state.armed and len(stub.state.received_commands) >= 1)
    master.close()
