import logging
import os
import sys
import daemon

from struct import pack
from collections import namedtuple
from enum import IntEnum
from crc16 import crc16xmodem
from time import sleep, time

from http.server import HTTPServer
from threading import Thread, Lock, Event

curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path:
    sys.path.append(root_dir)

from axpert.connector import resolve_connector                  # noqa
from axpert.cmd_parser import parse_args                        # noqa
from axpert.protocol import CMD_REL                             # noqa
from axpert.http_handler import create_base_remote_cmd_handler  # noqa


# Reset HTTP Server each X in seconds
RESET_SLEEP = 150 

FORMAT = '[%(asctime)s] %(message)s'
ENCODING = 'utf-8'

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


def reseteable_http_server(stop_event, start_event, connector):
    http_handler = create_base_remote_cmd_handler(
        atomic_execute, connector, CMD_REL
    )
    server = HTTPServer(('', 8889), http_handler)
    server.server_activate()
    while not stop_event.is_set(): 
        try:
            server.handle_request()
        except Exception as e:
            log.error(e)

    server.server_close()
    start_event.set()
    stop_event.clear()
    log.info('HTTP server stopped')


def start_http_server(stop_event, start_event, connector):
    log.info('Starting HTTP server')
    thread = Thread(
        target=reseteable_http_server, 
        args=[stop_event, start_event, connector]
    )
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

    last = time() 
    stop_event, start_event = Event(), Event()
    start_event.set()

    while True:
        with Connector(devices=args['devices'], log=log) as connector:
            start_event.wait()
            http_server = start_http_server(
                stop_event, start_event, connector
            )
            start_event.clear()

            while (last + RESET_SLEEP) > time():
                sleep(1)
            stop_event.set()
            last = time()

        log.info('Reseting Comms and HTTP')
            

if __name__ == '__main__':
    args = parse_args()

    if args['daemonize']:
        with daemon.DaemonContext() as c:
            logging.basicConfig(
                format=FORMAT, filename='{}/godenerg.log'.format(root_dir)
            )
            log = logging.getLogger('godenerg')
            log.setLevel(logging.DEBUG if args['verbose'] else logging.INFO)
            run_as_daemon(args)
    else:
        # TODO: must sort out this duplicity issue with logging.
        # if logger is out of deamonizer context, daemon does not work
        # must investigate
        logging.basicConfig(
            format=FORMAT, filename='{}/godenerg.log'.format(root_dir)
        )
        log = logging.getLogger('godenerg')
        log.setLevel(logging.DEBUG if args['verbose'] else logging.INFO)

        run_cmd(args)
