from collections import namedtuple
from json import dumps as json_dumps


CmdSpec=namedtuple('CmdSpec', ['code', 'size', 'val', 'json'])


def status_json_formatter(raw):
    structure = (
        ('mode','%s'), ('voltage_grid', '%f'),
        ('ac_watts', '%d'), ('batt_charge', '%f'),
        ('batt_charge_amps', '%d'), ('batt_charge_percent', '%d'),
        ('temp', '%d'), ('pv_amps', '%d'),
        ('pv_volts', '%f'), ('batt_charge_2', '%f'),
        ('batt_discharge_amps', '%d'), ('mask_a', '%d'),
        ('mask_b','%d'), ('mask_c', '%d'),
        ('pv_watts', '%d'), ('mask_d', '%d')
    )

    data = {
        label: form % token
        for (label, form), token in zip(structure, raw.split(' '))
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

