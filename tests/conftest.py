import socket

import pytest

from pwnuav.drone_stub import DroneStub


def _free_udp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def drone():
    port = _free_udp_port()
    stub = DroneStub(conn_str=f"udpin:127.0.0.1:{port}").start()
    conn_str = f"udpout:127.0.0.1:{port}"
    try:
        yield stub, conn_str
    finally:
        stub.stop()
