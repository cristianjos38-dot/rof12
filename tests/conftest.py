import os
import socket

import pytest

os.environ.setdefault("MODEL_MODE", "mock")


def pytest_addoption(parser):
    parser.addoption("--disable-socket", action="store_true", help="fail tests that attempt network sockets")


@pytest.fixture(autouse=True)
def disable_socket_when_requested(request, monkeypatch):
    if request.config.getoption("--disable-socket"):
        def blocked_socket(*args, **kwargs):
            raise AssertionError("network socket disabled for deterministic tests")

        monkeypatch.setattr(socket, "socket", blocked_socket)

