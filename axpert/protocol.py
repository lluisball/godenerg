from collections import namedtuple

CmdSpec=namedtuple('CmdSpec', ['code', 'size', 'val', 'json'])


def status_json_formatter(raw):
    return raw


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

