from pwnuav.link import connect, announce, wait_heartbeat


def test_connect_returns_mavfile():
    master = connect("udpout:127.0.0.1:59000")
    assert hasattr(master, "mav")
    assert master.mav.srcSystem == 255
    master.close()


def test_connection_uses_mavlink2():
    master = connect("udpout:127.0.0.1:59001")
    assert master.WIRE_PROTOCOL_VERSION == "2.0"
    master.close()


def test_wait_heartbeat_returns_heartbeat(drone):
    _, conn = drone
    master = connect(conn)
    announce(master)
    hb = wait_heartbeat(master, timeout=5)
    assert hb is not None
    assert hb.get_type() == "HEARTBEAT"
    master.close()
