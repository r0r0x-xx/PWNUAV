from pwnuav.link import announce, connect
from pwnuav.gps_spoof import spoof_position
from tests._util import wait_until


def test_gps_spoof_moves_reported_position(drone):
    _, conn = drone
    master = connect(conn)
    announce(master)
    master.wait_heartbeat(timeout=5)
    spoof_position(master, lat=6.2518, lon=-75.5636, alt=1500)

    def moved():
        m = master.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=0.5)
        return m is not None and abs(m.lat / 1e7 - 6.2518) < 0.001 \
            and abs(m.lon / 1e7 - (-75.5636)) < 0.001
    assert wait_until(moved, timeout=5)
    master.close()
