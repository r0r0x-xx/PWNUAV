from pwnuav.eavesdrop import run_eavesdrop


def test_eavesdrop_reads_position_and_battery(drone):
    _, conn = drone
    t = run_eavesdrop(conn, duration=3.0)
    assert t.lat is not None and abs(t.lat - 37.7749) < 0.001
    assert t.lon is not None and abs(t.lon - (-122.4194)) < 0.001
    assert t.battery_v is not None and abs(t.battery_v - 12.0) < 0.1
    assert t.battery_pct == 75


def test_eavesdrop_reads_attitude(drone):
    _, conn = drone
    t = run_eavesdrop(conn, duration=3.0)
    assert t.yaw is not None and abs(t.yaw - 1.57) < 0.01
