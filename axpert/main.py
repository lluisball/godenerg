import logging
import os
import sys
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

from axpert.connector import resolve_connector                  # noqa
from axpert.cmd_parser import parse_args                        # noqa
from axpert.protocol import CMD_REL                             # noqa
from axpert.http_handler import create_base_remote_cmd_handler  # noqa


FORMAT = '[%(asctime)s] %(message)s'
ENCODING = 'utf-8'

NAK, ACK = 'NAK', 'ACK'

Response = namedtuple('Response', ['status', 'data'])
logging.basicConfig(
    format=FORMAT, filename='{}/gonederg.log'.format(root_dir)
)
log = logging.getLogger('gonederg')


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


def output_as_json(args):
    return 'format' in args          \
        and args['format'] == 'json' \
        and args['cmd'].json


def run_cmd(args):
    Connector = resolve_connector(args)
    with Connector(log=log, devices=args['devices']) as connector:
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


def start_http_server(connector):
    log.info('Starting HTTP server')

    server = HTTPServer(
        ('', 8889),
        create_base_remote_cmd_handler(
            atomic_execute, connector, CMD_REL
        )
    )
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    log.info('HTTP server started')


def start_process_executer(connector, cmd):
    log.info('Starting process executer')
    log.info('Started process executer')


def start_data_logger(connector, cmd):
    log.info('Starting data logger')
    log.info('Started data logger')


def atomic_execute(connector, cmd):
    with Lock():
        return execute(connector, cmd)


def run_as_daemon(args):
    Connector = resolve_connector(args)
    cmd = args['cmd']
    log.info('Starting Godenerg as daemon')

    with Connector(devices=args['devices'], log=log) as connector:
        start_http_server(connector)
        start_process_executer(connector, cmd)
        start_data_logger(connector, cmd)

        while True:
            sleep(1)


def setup_logger():
    return log


if __name__ == '__main__':
    args = parse_args()
    log.setLevel(logging.DEBUG if args['verbose'] else logging.INFO)

    if args['daemonize']:
        #with daemon.DaemonContext() as c:
        run_as_daemon(args)
    else:
        run_cmd(args)
