from functools import reduce
from argparse import ArgumentParser
from axpert.protocol import CMD_REL, CmdSpec


def validate_args(args):
    if args['serial'] and args['usb']:
        print('\nYou must choose between serial communications '
              ' or usb communications but not both!')
        exit(1)

    if (args['value'] or args['size']) and not args['cmd']:
        print('\nIf you specify a value you must also specify a command\n')
        exit(1)

    return args


def find_cmd(args):
    for cmd, cmd_spec in CMD_REL.items():
        if cmd in args and args[cmd]:
            return cmd_spec


def parse_raw_command_line_execution_params(parser):
    parser.add_argument(
        '-c', '--cmd', dest='cmd',
        help='Command to execute, if specified any other commands'
             '(--status, --op-mode...) will be ignored.'
    )
    parser.add_argument(
        '-v', '--value', dest='value',
        help='Value for command that sets configuration'
    )
    parser.add_argument(
        '-s', '--size', dest='size',
        type=int, help='Expected response size for command'
    )
    return parser


def parse_specified_command_line_execution_params(parser):
    parser.add_argument(
        '--status', dest='status', default=False,
        help='Current status [QPIGS]', action='store_true'
    )
    parser.add_argument(
        '--op-mode', dest='operation_mode', default=False,
        help='Shows the operation mode [QMOD]', action='store_true'
    )
    parser.add_argument(
        '-f', '--format', dest='output_format', default='raw',
        help='Output format for response', choices=['raw', 'json']
    )
    return parser


def parse_connection_params(parser):
    parser.add_argument(
        '--usb', action='store_true',
        help='Connect trough usbhid device', dest='usb'
    )
    parser.add_argument(
        '--serial', action='store_true',
        help='Connect trough serial device', dest='serial'
    )
    parser.add_argument(
        '-d', '--device', dest='devices', action='append',
        help='Serial ports to scan for device',
    )
    return parser


def parse_datalogging_extraction_params(parser):
    parser.add_argument(
        '--extract-csv-data', dest='extract_csv_data', action='store',
        help='Extract a data range from the datalogger store'
             ' as a csv file'
    )
    parser.add_argument(
        '--extract-json-data', dest='extract_json_data', action='store',
        help='Extract a data range from the datalogger store'
             ' as a json file'
    )

    parser.add_argument(
        '--extract-file', dest='extract_file', action='store',
        help='File where to save the extracted datalogging'
    )
    parser.add_argument(
        '--col', dest='extract_cols', action='append',
        help='File where to save the extracted datalogging'
    )
    return parser


def parse_core_params(parser):
    parser.add_argument(
        '--daemon', dest='daemonize', action='store_true',
        help='Run as a daemon with a http server and a datalogger',
        default=False
    )

    parser.add_argument(
        '--verbose', dest='verbose', action='store_true',
        help='Verbose debug data', default=False
    )
    return parser


def compose_datalogging_response(args, response):
    if 'extract_csv_data' not in args and 'extract_json_data' not in args:
        return response

    if args['extract_csv_data']:
        response['extract'] = 'csv'
        response['range'] = args['extract_csv_data']
    elif args['extract_json_data']:
        response['extract'] = 'json'
        response['range'] = args['extract_json_data']

    response['file'] = args['extract_file']
    response['cols'] =                                      \
        args['extract_cols']                                \
        if 'extract_cols' in args and args['extract_cols']  \
        else None

    return response


def compose_raw_command_line_response(args, response):
    if 'cmd' not in args or args['cmd'] is None:
        return response

    response['cmd'] = CmdSpec(
        code=args['cmd'], size=args['size'],
        val=args['value'], json=None
    )

    return response


def compose_specified_command_line_response(args, response):
    specified_cmds = ('status', 'operation_mode')

    if not any(args.get(cmd, False) for cmd in specified_cmds):
        return response

    response['cmd'] = find_cmd(args)
    response['format'] = args['output_format']
    return response


def compose_connection_response(args, response):
    conn_res = {
        'devices': args['devices'],
        'serial': args['serial'],
        'usb': args['usb']
    }
    return {**conn_res, **response}


def compose_core_response(args, response):
    core_res = {
        'daemonize': args['daemonize'],
        'verbose': args['verbose']
    }
    return {**core_res, **response}


def parse_args():
    parser_fnxs = [
        parse_connection_params, parse_core_params,
        parse_raw_command_line_execution_params,
        parse_specified_command_line_execution_params,
        parse_datalogging_extraction_params
    ]

    compose_response_fnxs = [
        compose_connection_response, compose_core_response,
        compose_raw_command_line_response,
        compose_specified_command_line_response,
        compose_datalogging_response
    ]

    parser = reduce(
        lambda parser, fnx: fnx(parser),
        parser_fnxs,
        ArgumentParser(prog='main.py')
    )

    args = vars(parser.parse_args())
    return reduce(
        lambda response, fnx: fnx(args, response),
        compose_response_fnxs,
        validate_args(args)
    )
