import pytest

from json import loads as json_loads

from axpert.protocol import (
    status_json_formatter, parse_device_status,
    SOLAR_CHARGING, AC_CHARGING, Status,
    parse_response_status
)


def test_status_format():
    test_raw_data =                                             \
        b'(000.0 00.0 230.0 50.0 0184 0071 003 404 50.10 000 '  \
        b'079 0049 0000 000.0 00.00 00001 01010000 00 00 00000' \
        b' 010\x1d\xc2\xb9\r\x00\x00'

    result = status_json_formatter(test_raw_data.decode('utf-8'))
    assert result and isinstance(result, str)
    json_result = json_loads(result)
    assert isinstance(json_result, dict)

    result = status_json_formatter(
        test_raw_data.decode('utf-8'), serialize=False
    )
    assert result and isinstance(result, dict)
    assert result['grid_volt'] == 0.0 and result['grid_freq'] == 0.0
    assert result['ac_volt'] == 230.0 and result['ac_freq'] == 50.0
    assert result['ac_va'] == 184 and result['ac_watt'] == 71
    assert result['load_percent'] == 3 and result['bus_volt'] == 404
    assert result['batt_volt'] == 50.1 and result['batt_charge_amps'] == 0
    assert result['batt_capacity'] == 79 and result['temp'] == 49
    assert result['pv_amps'] == 0 and result['pv_volts'] == 0.0
    assert result['batt_volt_scc'] == 0.0
    assert result['batt_discharge_amps'] == 1
    assert result['raw_status'] == '01010000'
    assert result['mask_b'] == '00' and result['mask_c'] == '00'
    assert result['pv_watts'] == 0 and result['mask_d'] == '010'
    assert result['charge_source'] == []
    assert result['batt_volt_to_steady'] is False
    assert result['load_status'] is True
    assert result['ssc_firmware_updated'] is False
    assert result['configuration_changed'] is True
    assert result['sbu_priority_version'] is False


@pytest.mark.parametrize(
    'data, expected', [
        ('00000000',
         {'charge_source': [], 'batt_volt_to_steady': False,
          'load_status': False, 'ssc_firmware_updated': False,
          'configuration_changed': False, 'sbu_priority_version': False}),
        ('11111111',
         {'charge_source': [AC_CHARGING, SOLAR_CHARGING],
          'batt_volt_to_steady': True, 'load_status': True,
          'ssc_firmware_updated': True, 'configuration_changed': True,
          'sbu_priority_version': True}),
        ('10011110',
         {'charge_source': [SOLAR_CHARGING],
          'batt_volt_to_steady': True, 'load_status': True,
          'ssc_firmware_updated': False, 'configuration_changed': False,
          'sbu_priority_version': True}),
        ('011110', {}),
        (4096, {}),
        (None, {})
    ]
)
def test_parse_device_status(data, expected):
    assert parse_device_status(data) == expected


@pytest.mark.parametrize(
    'data, expected', [
        ('lalfdasfdas NAKfdsfa', Status.KO),
        ('NAK dfdfas', Status.KO),
        ('(ACK\r', Status.OK),
        ('fdsaf', Status.NN),
        (None, Status.NN)
    ]
)
def test_parse_response(data, expected):
    assert parse_response_status(data) == expected
