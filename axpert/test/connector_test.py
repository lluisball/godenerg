from unittest.mock import patch, Mock

from axpert.connector_serial import (
    SerialConnector, MAX_CONNECT_RETRIES
)

from axpert.connector import resolve_connector


class MockConnectorA():
    pass


class MockConnectorB():
    pass


def test_serial_reconnect():
    MockException = Mock()

    class MockSerial(Mock):
        fail = False

        def __init__(self, *args, **kwargs):
            super(MockSerial, self).__init__(*args, **kwargs)

        @classmethod
        def enable_fail(cls):
            cls.fail = True

        def read(self, *args):
            if self.fail:
                raise MockException()
            else:
                return 'a' * 20

        def close(self):
            pass

    with patch('axpert.connector_serial.Serial', MockSerial) as mock_serial, \
            patch('axpert.connector_serial.SerialException', MockException), \
            patch('axpert.connector_serial.sleep') as mock_sleep,            \
            patch('axpert.connector_serial.exit') as mock_exit:

        with SerialConnector(devices=['/dev/ttyUSB0'], log=Mock()) as connector:
            # Proper read
            res = connector.read(20)
            assert res and res == 'a' * 20

            # Force fail and make sure we retry
            mock_serial.enable_fail()
            res = connector.read(20)
            mock_exit.assert_called_once_with(1)
            assert mock_sleep.call_count == MAX_CONNECT_RETRIES


def test_resolve_connector():
    mock_registry = {
        'con_a': 'axpert.test.connector_test.MockConnectorA',
        'con_b': 'axpert.test.connector_test.MockConnectorB'
    }

    with patch('axpert.connector.connector_registry', mock_registry):
        connector_a = resolve_connector({'con_a': True})
        assert connector_a.__name__ == MockConnectorA.__name__

        connector_b = resolve_connector({'con_a': False, 'con_b': True})
        assert connector_b.__name__ == MockConnectorB.__name__

        bad_connector = resolve_connector({'con_c': True})
        assert bad_connector is None
