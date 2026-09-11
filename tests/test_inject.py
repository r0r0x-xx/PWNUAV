from pymavlink import mavutil

from pwnuav.link import announce, connect
from pwnuav.inject import send_arm, send_set_mode, wait_ack
from tests._util import wait_until


def test_injection_arms_vehicle(drone):
    stub, conn = drone
    master = connect(conn)
    announce(master)
    master.wait_heartbeat(timeout=5)
    send_arm(master, arm=True)
    result = wait_ack(master, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)
    assert result == mavutil.mavlink.MAV_RESULT_ACCEPTED
    assert wait_until(lambda: stub.state.armed is True)
    master.close()


def test_injection_changes_mode(drone):
    stub, conn = drone
    master = connect(conn)
    announce(master)
    master.wait_heartbeat(timeout=5)
    send_set_mode(master, custom_mode=4)  # 4 = GUIDED in ArduCopter
    result = wait_ack(master, mavutil.mavlink.MAV_CMD_DO_SET_MODE)
    assert result == mavutil.mavlink.MAV_RESULT_ACCEPTED
    assert wait_until(lambda: stub.state.custom_mode == 4)
    master.close()
