import pytest

from unittest.mock import patch

from axpert.cmd_parser import (find_cmd, validate_args, parse_args)

@pytest.mark.parametrize(
    'cmd_data, expected', [
        ({'cmd_1': True}, {'cmd': 'A', 'size': 1}),
        ({'cmd_2': True}, {'cmd': 'B', 'size': 2}),
        ({'not_cmd': True}, None),
        ({'cmd_1': False}, None)
    ]
)
def test_find_cmd(cmd_data, expected):
    MOCK_CMD_REL = {
        'cmd_1': ('A', 1),
        'cmd_2': ('B', 2)
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
    ({'cmd': 'QQQ', 'size': 120,
       'serial': True, 'usb': False,
       'devices': None, 'value': '33.3'},
     {'cmd': 'QQQ', 'serial': True, 'usb': False,
         'size': 120, 'val': '33.3'}),
     ({'info': True, 'serial': False, 'usb': True,
       'devices': None, 'value': None, 'size': None},
      {'cmd': 'QPAS', 'serial': False, 'usb': True,
       'size': 66, 'val': None})
    ]
)
def test_parse_args(mock_parse_args, expected):
    mock_cmd_rel = {'info': ('QPAS', 66)}

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


