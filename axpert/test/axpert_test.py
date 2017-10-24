import pytest

from struct import pack
from unittest.mock import patch, Mock

from axpert.connector import Connector
from axpert.protocol import CmdSpec
from axpert.main import (
    Status, parse_response_status, execute
)


class MockConnector(Connector):
    def __init__(self, devices=None):
        self.write_buffer = []

    def read(self, size):
        return 'X' * size

    def write(self, data):
        self.write_buffer.append(data)

    def open(self):
        pass

    def close(self):
        pass


@pytest.mark.parametrize(
    'data, expected',[
        ('lalfdasfdas NAKfdsfa', Status.KO),
        ('NAK dfdfas', Status.KO),
        ('(ACK\r', Status.OK),
        ('fdsaf', Status.NN),
        (None, Status.NN)
    ]
)
def test_parse_response(data, expected):
    assert parse_response_status(data) == expected


def test_execute_two_packets():
    mock_connector = MockConnector()

    msg = 'QQQ'
    val = '33.2'
    expected_crc = 0xC099
    crc = pack('>H', expected_crc)
    cmd = CmdSpec(code=msg, val=val, size=8, json=None)
    execute(mock_connector, cmd)

    # Writes to device should happen in writes of 8 bytes;
    #  expect 2 writes. The last write can be smaller than 8
    #  since includes the end of comms marker '\r'
    assert len(mock_connector.write_buffer) == 2
    first_packet, second_packet = mock_connector.write_buffer

    expected_full_write = (msg + val).encode() + crc + b'\r'
    first_expected = expected_full_write[:8]
    second_expected = expected_full_write[8:]

    assert first_expected == first_packet
    assert second_expected == second_packet


def test_execute_single_packets():
    mock_connector = MockConnector()

    msg = 'QPIGS'
    expected_crc = 0xB7A9
    crc = pack('>H', expected_crc)
    cmd = CmdSpec(code=msg, val='', size=8, json=None)
    execute(mock_connector, cmd)

    assert len(mock_connector.write_buffer) == 1
    first_packet = mock_connector.write_buffer[0]

    expected_full_write = msg.encode() + crc + b'\r'
    assert expected_full_write == first_packet
