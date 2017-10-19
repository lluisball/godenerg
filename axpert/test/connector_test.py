import pytest

from unittest.mock import patch, Mock
from axpert.connector_serial import (
    SerialConnector, MAX_CONNECT_RETRIES
)


def test_serial_reconnect():
    MockSerialException = Mock()

    class MockSerial(Mock):

        fail = False

        def __init__(self, *args, **kwargs):
            super(MockSerial, self).__init__(*args, **kwargs)

        @classmethod
        def enable_fail(cls):
            cls.fail = True

        def read(self, *args):
            if self.fail:
                raise MockSerialException()
            else:
                return 'a' * 20

        def close(self):
            pass

    with patch('axpert.connector_serial.Serial', MockSerial) as mock_serial, \
            patch('axpert.connector_serial.SerialException',                 \
                  MockSerialException),                                      \
            patch('axpert.connector_serial.sleep') as mock_sleep,            \
            patch('axpert.connector_serial.exit') as mock_exit:

        with SerialConnector(devices=['/dev/ttyUSB0']) as connector:
            #Proper read
            res = connector.read(20)
            assert res and res == 'a' * 20

            #Force fail and make sure we retry
            mock_serial.enable_fail()
            res = connector.read(20)
            mock_exit.assert_called_once_with(1)
            assert mock_sleep.call_count == MAX_CONNECT_RETRIES
