from collections import namedtuple
from json import dumps as json_dumps


CmdSpec=namedtuple('CmdSpec', ['code', 'size', 'val', 'json'])


def status_json_formatter(raw):
    structure = (
        ('grid_volt', '%f'), ('grid_freq', '%f'),
        ('ac_volt', '%f'), ('ac_freq', '%f'),
        ('ac_va', '%d'), ('ac_watt', '%d'),
        ('load_percent', '%f'), ('bus_volt', '%f'),
        ('batt_volt'), ('batt_charge_amps'),
        ('batt_capacity'), ('temp', '%d'),
        ('pv_amps', '%d'), ('pv_volts', '%f'),
        ('batt_volt_scc', '%f'), ('batt_discharge_amps', '%d'),
        ('device_status', '%s'),
        ('mask_b','%d'), ('mask_c', '%d'),
        ('pv_watts', '%d'), ('mask_d', '%d')
    )

    # Ignore initial '(' and end 2 byte CRC and split
    raw_tokens = raw[1:-2].split(' ')

    data = {
        label: (form % float(token) if not '%s' in token else token)
        for (label, form), token in zip(structure, raw_tokens)
    }

    return json_dumps(data)


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

