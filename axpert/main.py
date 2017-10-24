import os, sys
import daemon

from struct import pack
from collections import namedtuple
from enum import IntEnum
from crc16 import crc16xmodem
from time import sleep

from http.server import HTTPServer
from threading import Thread, Lock

curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path:
    sys.path.append(root_dir)

from axpert.connector import resolve_connector
from axpert.cmd_parser import parse_args
from axpert.protocol import CMD_REL
from axpert.http_handler import create_base_remote_cmd_handler


NAK, ACK = 'NAK', 'ACK'

Response = namedtuple('Response', ['status', 'data'])


class Status(IntEnum):
    OK = 1
    KO = 2
    NN = 3


def parse_response_status(data):
    if not data or (ACK not in data and NAK not in data):
        return Status.NN
    elif ACK in data:
        return Status.OK
    elif NAK in data:
        return Status.KO


def execute(connector, cmd):
    value = cmd.val if cmd.val else ''
    encoded_cmd = cmd.code.encode() + value.encode()
    checksum = crc16xmodem(encoded_cmd)
    request = encoded_cmd + pack('>H', checksum) + b'\r'
    # No commands take more than 16 bytes
    # Take first 8 and second 8 if any
    connector.write(request[:8])
    if len(request) > 8:
        connector.write(request[8:])

    response = connector.read(int(cmd.size))
    return Response(data=response, status=parse_response_status(response))


def output_as_json(args):
    return 'format' in args          \
        and args['format'] == 'json' \
        and args['cmd'].json


def run_cmd(args):
    Connector = resolve_connector(args)
    with Connector(devices=args['devices']) as connector:
        cmd = args['cmd']
        response = execute(connector, cmd)
        if response.status == Status.OK or response.status == Status.NN:
            if output_as_json(args):
                print(cmd.json(response.data))
            else:
                print(response.data)
        elif response.status == Status.KO:
            print("\nCommand not understood by inverter:\n")
            print(response.data)
            print('\n')



def start_http_server(connector, cmds):
    print ('> starting http server')
    cmds = [
        ('status', CMD_REL['status']),
        ('mode', CMD_REL['operation_mode'])
    ]
    server = HTTPServer(
        ('', 8889),
        create_base_remote_cmd_handler(
            atomic_execute, connector, cmds
        )
    )
    thread = Thread(target = server.serve_forever)
    thread.daemon = True
    thread.start()
    print('> http server started')


def start_process_executer(connector, cmd):
    pass


def data_logger(connector, cmd):
    pass


def atomic_execute(connector, cmd):
    with Lock():
        return execute(connector, cmd)


def run_as_daemon(cntx, args):
    Connector = resolve_connector(args)
    cmd = args['cmd']
    with Connector(devices=args['devices']) as connector:
        start_http_server(connector, cmd)
        start_process_executer(connector, cmd)

        while True:
            data_logger(connector, cmd)
            sleep(1)


if __name__ == '__main__':
    args = parse_args()
    if args['daemonize']:
        with daemon.DaemonContext() as cntx:
            run_as_daemon({}, args)
    else:
        run_cmd(args)
