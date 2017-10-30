import logging
import os
import sys
import daemon

from urllib.request import urlopen
from socket import timeout
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


WATCHDOG_URL = 'http://localhost:8889/cmds?cmd=operation_mode'
WATCHDOG_MAX_TIMEOUT = 5
WATCHDOG_INTERVAL = 10
WATCHDOG_CONNECTOR_RETRY = 5

FORMAT = '[%(asctime)s] %(message)s'
LOG_FILE = '{}/godenerg.log'.format(root_dir)
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


def reseteable_http_server(connector):
    http_handler = create_base_remote_cmd_handler(
        atomic_execute, connector, CMD_REL
    )
    server = HTTPServer(('', 8889), http_handler)
    server.server_activate()
    while True:
        try:
            server.handle_request()
        except Exception as e:
            log.error(e)


def start_http_server(connector):
    log.info('Starting HTTP server')
    thread = Thread(
        target=reseteable_http_server,
        args=[connector]
    )
    thread.start()
    log.info('HTTP server started')
    return thread


def start_process_executer(connector, cmd):
    log.info('Starting process executer')
    log.info('Started process executer')


def start_data_logger(connector, cmd):
    log.info('Starting data logger')
    log.info('Started data logger')


def atomic_execute(connector, cmd):
    with Lock():
        return execute(connector, cmd)


def watchdog_http_server(fail_event):
    if not fail_event.is_set():
        try:
            response = urlopen(WATCHDOG_URL, timeout = WATCHDOG_MAX_TIMEOUT)
            response.read()
            log.debug('Watchdog HTTP server call OK')
        except timeout:
            fail_event.set()
    else:
        log.debug(
            'HTTP server fail event set, cannot watchdog'
            ' waiting to do http server watchdog'
        )

def watchdog_connector(connector, fail_event=None):
    cmd = CMD_REL['operation_mode']

    try:
        res = execute(connector, cmd)
        if not res or res.status not Status.OK:
            raise ValueError('Bad connector response value to watchdog query')
        return True

    except ValueError as ve:
        if fail_event:
            fail_event.set()
        return False


def watchdog(connector, connector_fail_event, http_server_fail_event):
    try:
        while True:
            sleep(WATCHDOG_INTERVAL)
            watchdog_connector(connector, connector_fail_event)
            watchdog_http_server(http_server_fail_event)

    except Exception as e:
        log.error(e)


def start_watchdog(connector, connector_fail_event, http_server_fail_event):
    log.info('Starting Watchdog')
    thread = Thread(
        target=watchdog,
        args=[
            connector,
            connector_fail_event,
            http_server_fail_event
        ]
    )
    thread.start()
    log.info('Watchdog started')
    return thread


def check_http_server(connector, http_server, fail_event):
    if not fail_event.is_set():
        return http_server

    log.error('HTTP Server fail event fired')
    http_server.join(timeout=1)
    http_server = start_http_server(connector)
    fail_event.clear()


def check_connector(connector, devices, fail_event):
    if not fail_event.is_set():
        return connector

    log.error('Connector fail event fired')
    retry = 0
    while retry < WATCHDOG_CONNECTOR_RETRY:
        try:
            connector.close()
        except:
            pass

        sleep(retry * 3)
        connector = Connector(devices = devices, log=log)
        connector.open()
        sleep(0.25)
        connector_ok = watchdog_connector(connector)
        if connector_ok:
            fail_event.clear()
            return connector
        retry += 1

    return None


def connector_error_stop_daemon(daemon, http_server, watchdog):
    log.error('Could not connect to Inverter after many retries...')
    log.error('Stopping daemon')
    http_server.join(timeout=0.1)
    watchdog.join(timeout=0.1)
    daemon.terminate()


def run_as_daemon(daemon, args):
    Connector = resolve_connector(args)
    cmd = args['cmd']
    devices = args['devices']
    log.info('Starting Godenerg as daemon')

    http_server_fail_event = Event()
    connector_fail_event = Event()

    connector = Connector(devices=devices, log=log)
    try:
        connector.open()
        http_server = start_http_server(connector)
        watchdog = start_watchdog(
            connector, connector_fail_event, http_server_fail_event
        )

        while True:
            # Check connector, if we could not get a connector back
            # stop the daemon. Nothing we can do without connector.
            connector = check_connector(
                connector, devices, connector_fail_event
            )
            if not connector:
                connector_error_stop_daemon(daemon, http_server, watchdog)
                break

            # Check HTTP server, logger and task processor
            http_server = check_http_server(
                connector, http_server, http_server_fail_event
            )

            sleep(1)

    except Exception as e:
        log.error(e)

    finally:
        if connector:
            connector.close()


if __name__ == '__main__':
    args = parse_args()
    log_level = logging.DEBUG if args['verbose'] else logging.INFO

    if args['daemonize']:
        with daemon.DaemonContext() as daemon:
            logging.basicConfig(format=FORMAT, filename=LOG_FILE)
            log = logging.getLogger('godenerg')
            log.setLevel(log_level)
            run_as_daemon(daemon, args)
    else:
        log = logging.getLogger('godenerg')
        log.setLevel(log_level)
        log.addHandler(logging.StreamHandler(sys.stdout))
        run_cmd(args)
