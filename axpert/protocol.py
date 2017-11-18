from collections import namedtuple
from json import dumps as json_dumps
from struct import pack
from crc16 import crc16xmodem
from enum import IntEnum

"""
"""


CmdSpec = namedtuple('CmdSpec', ['code', 'size', 'val', 'json'])
Response = namedtuple('Response', ['status', 'data'])
InverterConf = namedtuple('Inverter', ['bulk_volt', 'float_volt'])

SOLAR_CHARGING = 'solar_charging'
AC_CHARGING = 'ac_charging'
NOT_CHARGING = 'not_charging'
NAK, ACK = 'NAK', 'ACK'


class Status(IntEnum):
    OK = 1
    KO = 2
    NN = 3


def empty_inverter_conf():
    return InverterConf(bulk_volt=None, float_volt=None)


def parse_inverter_conf(data):
    BULK_VOL_COL, FLOAT_VOL_COL = 10, 11
    try:
        tokens = data.split(' ')
        return InverterConf(
            bulk_volt=float(tokens[BULK_VOL_COL]),
            float_volt=float(tokens[FLOAT_VOL_COL])
        )
    except:
        return empty_inverter_conf()


def execute(log, connector, cmd):
    value = cmd.val if cmd.val else ''
    encoded_cmd = cmd.code.encode() + value.encode()
    checksum = crc16xmodem(encoded_cmd)
    request = encoded_cmd + pack('>H', checksum) + b'\r'

    log.debug(
        'Request {} done as "{}"'.format(
            cmd, request
        )
    )

    # No commands take more than 16 bytes
    # Take first 8 and second 8 if any
    connector.write(request[:8])
    if len(request) > 8:
        connector.write(request[8:])

    response = connector.read(int(cmd.size))
    log.debug('Response from connector to {} is:'.format(cmd))
    log.debug(response)

    return Response(data=response, status=parse_response_status(response))


def parse_response_status(data):
    if not data or (ACK not in data and NAK not in data):
        return Status.NN
    elif ACK in data:
        return Status.OK
    elif NAK in data:
        return Status.KO


def parse_device_status(raw_status):
    if not raw_status                           \
            or not isinstance(raw_status, str)  \
            or len(raw_status) < 8:
        return {}

    charge_sources = {0b101: AC_CHARGING, 0b110: SOLAR_CHARGING}
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

    def _clean_val(val):
        if not val or val=='NA':
            return 0
        else:
            return val

    types = {'s': str, 'f': float, 'd': int}

    for frm, type_fnx in types.items():
        if frm in frmt:
            return lambda txt: type_fnx(frmt % type_fnx(_clean_val(txt)))

    return lambda txt: txt % frmt


def status_json_formatter(raw, serialize=True):
    to_float = typer('%.2f')
    to_int = typer('%d')
    to_str = typer('%s')

    structure = (
        ('grid_volt', to_float), ('grid_freq', to_float),
        ('ac_volt', to_float), ('ac_freq', to_float),
        ('ac_va', to_int), ('ac_watt', to_int),
        ('load_percent', to_int), ('bus_volt', to_int),
        ('batt_volt', to_float), ('batt_charge_amps', to_int),
        ('batt_capacity', to_int), ('temp', to_int),
        ('pv_amps', to_int), ('pv_volts', to_float),
        ('batt_volt_scc', to_float), ('batt_discharge_amps', to_int),
        ('raw_status', to_str),
        ('mask_b', to_str), ('mask_c', to_str),
        ('pv_watts', to_int), ('mask_d', to_str)
    )

    if not raw:
        return None

    # Ignore initial '(' and end 5 byte split
    raw_tokens = raw[1:-5].split(' ')
    data = {
        label: formatter(token)
        for (label, formatter), token in zip(structure, raw_tokens)
    }

    struct = {
        **data, **parse_device_status(data.get('raw_status', '00000000'))
    }
    return json_dumps(struct) if serialize else struct


def operation_json_formatter(raw, serialize=True):
    modes = {
        'P': 'PM', 'S': 'SB',
        'L': 'LN', 'B': 'BT',
        'F': 'FA', 'H': 'PS'
    }
    if not raw:
        return None
    mode_code = raw[1]
    data = {'mode': modes.get(mode_code, '00')}
    return json_dumps(data) if serialize else data


CMD_REL = {
    'status': CmdSpec(
        code='QPIGS', size=110, val='',
        json=status_json_formatter
    ),
    'settings': CmdSpec(
        code='QPIRI', size=110, val='',
        json=None
    ),
    'default_settings': CmdSpec(
        code='QDI', size=81, val='',
        json=None
    ),
    'operation_mode': CmdSpec(
        code='QMOD', size=5, val='',
        json=operation_json_formatter
    )
}
