from argparse import ArgumentParser
from axpert.protocol import CMD_REL


def validate_args(args):
    if args['serial'] and args['usb']:
        print('\nYou must choose between serial communications '
              ' or usb communications but not both!')
        exit(1)

    if (args['value'] or args['size']) and not args['cmd']:
        print('\nIf you specify a value you must also specify a command\n')
        exit(1)


def find_cmd(args):
    
    for cmd, (op_code, size) in CMD_REL.items():
        if cmd in args and args[cmd]:
            return {'cmd': op_code, 'size': size}


def parse_args():
    parser = ArgumentParser(prog='axpert.py')

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

    args = vars(parser.parse_args())
    validate_args(args)
    if 'cmd' in args and args['cmd'] is not None:
        cmd_data = {'cmd': args['cmd'], 'size': args['size']}
    else:
        cmd_data = find_cmd(args)

    return {
        **cmd_data, 'val': args['value'], 'devices': args['devices'],
        'serial': args['serial'], 'usb': args['usb']
    }
