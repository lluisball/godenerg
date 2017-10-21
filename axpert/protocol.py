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
    data = int(raw_status, 2)

    return {
        'charge_source': [
            source for mask, source in charge_sources.items() 
            if (mask & data) == mask
        ],
        'batt_volt_to_steady': bool(8 & data),
        'load_status': bool(16 & data),
        'ssc_firmware_updated': bool(32 & data),
        'configuration_changed': bool(64 & data),
        'sbu_priority_version': bool(128 & data)
    }


def typer(frmt):
    types = {'s': str, 'f': float, 'd': int}

    for frm, type_fnx in types.items():
        if frm in frmt:
            return lambda txt:type_fnx(frmt % type_fnx(txt))

    return lambda txt: txt % frmt


def status_json_formatter(raw):
    to_float = typer('%.2f')
    to_int = typer('%d')
    to_str = typer('%s')

    structure = (
        ('grid_volt', to_float), ('grid_freq', to_float),
        ('ac_volt', to_float), ('ac_freq', to_float),
        ('ac_va', to_int), ('ac_watt', to_int),
        ('load_percent', to_float), ('bus_volt', to_float),
        ('batt_volt', to_float), ('batt_charge_amps', to_int),
        ('batt_capacity', to_int), ('temp', to_int),
        ('pv_amps', to_int), ('pv_volts', to_float),
        ('batt_volt_scc', to_float), ('batt_discharge_amps', to_int),
        ('raw_status', to_str),
        ('mask_b',to_int), ('mask_c', to_int),
        ('pv_watts', to_int), ('mask_d', to_int)
    )

    # Ignore initial '(' and end 5 byte split
    raw_tokens = raw[1:-5].split(' ')
    data = {
        label: formatter(token)
        for (label, formatter), token in zip(structure, raw_tokens)
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

