from collections import namedtuple
from json import dumps as json_dumps

"""
b'(000.0 00.0 230.0 50.0 0184 0071 003 404 50.10 000 079 0049 0000 000.0 00.00 00001 01010000 00 00 00000 010\x1d\xc2\xb9\r\x00\x00'
"""


CmdSpec=namedtuple('CmdSpec', ['code', 'size', 'val', 'json'])

SOLAR_CHARGING = 'solar_charging'
AC_CHARGING = 'ac_charging'
NOT_CHARGING = 'not_charging'

def parse_device_status(raw_status):
    charge_sources = {
        0b101: AC_CHARGING,
        0b110: SOLAR_CHARGING,
        0b000: NOT_CHARGING
    } 

    check_source = lambda mask, current: (mask & current) == mask 
    data = int(raw_status, 2)

    return {
        'charge_source': [
            source for mask, source in charge_sources.items() 
            if check_source(mask, data)
        ],
        'batt_volt_to_steady': bool(0b1000 & data),
        'load_status': bool(0b10000 & data),
        'ssc_firmware_updated': bool(0b100000 & data),
        'configuration_changed': bool(0b100000 & data),
        'sbu_priority_version': bool(0b1000000 & data)
    }


def status_json_formatter(raw):
    structure = (
        ('grid_volt', '%.2f'), ('grid_freq', '%.2f'),
        ('ac_volt', '%.2f'), ('ac_freq', '%.2f'),
        ('ac_va', '%d'), ('ac_watt', '%d'),
        ('load_percent', '%.2f'), ('bus_volt', '%.2f'),
        ('batt_volt', '%.2f'), ('batt_charge_amps', '%d'),
        ('batt_capacity', '%d'), ('temp', '%d'),
        ('pv_amps', '%d'), ('pv_volts', '%.2f'),
        ('batt_volt_scc', '%.2f'), ('batt_discharge_amps', '%d'),
        ('raw_status', '%s'),
        ('mask_b','%d'), ('mask_c', '%d'),
        ('pv_watts', '%d'), ('mask_d', '%d')
    )

    # Ignore initial '(' and end 5 byte split
    raw_tokens = raw[1:-5].split(' ')
    data = {
        label: (form % float(token) if not '%s' in form else token)
        for (label, form), token in zip(structure, raw_tokens)
    }
    return json_dumps({**data, **parse_device_status(data['raw_status'])})


def operation_json_formatter(raw):
    return raw


CMD_REL = {
    'status': CmdSpec(
        code='QPIGS', size=110, val='',
        json=status_json_formatter
    ),
    'operation_mode': CmdSpec(
        code='QMOD', size=5, val='',
        json=operation_json_formatter
    )
}

