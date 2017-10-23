import pytest

from unittest.mock import patch

from axpert.cmd_parser import (find_cmd, validate_args, parse_args)
from axpert.protocol import CmdSpec

@pytest.mark.parametrize(
    'cmd_data, expected', [
        ({'cmd_1': True}, CmdSpec(code='A', size=1, json=None, val=None)),
        ({'cmd_2': True}, CmdSpec(code='B', size=2, json=None, val=None)),
        ({'not_cmd': True}, None),
        ({'cmd_1': False}, None)
    ]
)
def test_find_cmd(cmd_data, expected):
    MOCK_CMD_REL = {
        'cmd_1': CmdSpec(code='A', size=1, json=None, val=None),
        'cmd_2': CmdSpec(code='B', size=2, json=None, val=None)
    }
    with patch('axpert.cmd_parser.CMD_REL', MOCK_CMD_REL):
        assert find_cmd(cmd_data) == expected

@pytest.mark.parametrize(
    'args_data, exit_val', [
        ({'serial': True, 'usb': True, 'value': 'a',
          'size': 1, 'cmd': 'cmd_a'}, 1),
        ({'serial': False, 'usb': True, 'value': 'a',
          'size': 1, 'cmd': None}, 1)
    ]
)
def test_validate_args(args_data, exit_val):
    with patch('axpert.cmd_parser.exit') as mock_exit:
        validate_args(args_data)
        mock_exit.assert_called_once_with(exit_val)


@pytest.mark.parametrize(
    'mock_parse_args, expected', [
    ({'cmd': 'QQQ', 'size': 120, 'serial': True,
      'usb': False, 'devices': None, 'value': '33.3',
      'output_format': 'raw', 'daemonize':False},
     {'cmd': CmdSpec(code='QQQ', size=120, val='33.3', json=None),
      'serial': True, 'usb': False}),
     ({'info': True, 'serial': False, 'usb': True,
       'devices': None, 'value': None, 'size': None,
       'output_format':'raw', 'daemonize':False},
      {'cmd': CmdSpec(code='QPAS', size=66, val=None, json=None),
       'serial': False, 'usb': True})
    ]
)
def test_parse_args(mock_parse_args, expected):
    mock_cmd_rel = {
        'info': CmdSpec(code='QPAS', size=66, json=None, val=None)
    }

    class MockArgParser():
        def __init__(self, *args, **kwargs):
            pass
        def add_argument(self, *args, **kwargs):
            pass
        def parse_args(self):
            for k, v in mock_parse_args.items():
                setattr(self, k, v)
            return self

    with patch('axpert.cmd_parser.ArgumentParser', MockArgParser), \
            patch('axpert.cmd_parser.CMD_REL', mock_cmd_rel):
        response = parse_args()
        assert isinstance(response, dict)
        for expected_k, expected_v in expected.items():
            assert response[expected_k] == expected_v


