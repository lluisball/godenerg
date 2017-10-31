import logging
import os
import sys
import daemon

from urllib.request import urlopen
from urllib.error import HTTPError

from time import sleep
from signal import SIGKILL

from http.server import HTTPServer
from threading import Thread, Lock, Event

curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path:
    sys.path.append(root_dir)

from axpert.connector import resolve_connector                  # noqa
from axpert.cmd_parser import parse_args                        # noqa
from axpert.http_handler import create_base_remote_cmd_handler  # noqa
from axpert.protocol import (
    CMD_REL, execute, Status
)        # noqa


WATCHDOG_URL = 'http://localhost:8889/cmds?cmd=operation_mode'
WATCHDOG_MAX_TIMEOUT = 10
WATCHDOG_INTERVAL = 10

FORMAT = '[%(asctime)s] %(message)s'
LOG_FILE = '{}/godenerg.log'.format(root_dir)
ENCODING = 'utf-8'


def output_as_json(args):
    return 'format' in args          \
        and args['format'] == 'json' \
        and args['cmd'].json


def run_cmd(args):
    Connector = resolve_connector(args)
    with Connector(log=log, devices=args['devices']) as connector:
        cmd = args['cmd']
        response = execute(log, connector, cmd)
        if response.status == Status.OK or response.status == Status.NN:
            if output_as_json(args):
                log.info(cmd.json(response.data))
            else:
                log.info(response.data)
        elif response.status == Status.KO:
            log.error("Command not understood by inverter:")
            log.error(response.data)


def http_server_create(connector_cls, devices):
    http_handler = create_base_remote_cmd_handler(
        connector_cls, devices, atomic_execute, CMD_REL
    )
    server = HTTPServer(('', 8889), http_handler)
    server.server_activate()
    while True:
        try:
            server.handle_request()
        except Exception as e:
            log.error(e)


def start_http_server(connector_cls, devices):
    log.info('Starting HTTP server')
    thread = Thread(
        target=http_server_create,
        args=[connector_cls, devices]
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


def atomic_execute(connector_cls, devices, cmd):
    with Lock():
        with connector_cls(devices=devices, log=log) as connector:
            return execute(log, connector, cmd)


def watchdog_http_server(fail_event):
    if not fail_event.is_set():
        try:
            response = urlopen(WATCHDOG_URL, timeout=WATCHDOG_MAX_TIMEOUT)
            response.read()
            log.debug('Watchdog HTTP server call OK')
        except HTTPError as he:
            log.debug('Watchdog HTTP server call KO but got an answer')
        except Exception as e:
            fail_event.set()
            log.debug('Setting HTTP server fail event')
            log.error(e)
    else:
        log.debug(
            'HTTP server fail event set, cannot watchdog'
            ' waiting to do http server watchdog'
        )


def watchdog(http_server_fail_event):
    try:
        while True:
            sleep(WATCHDOG_INTERVAL)
            watchdog_http_server(
                http_server_fail_event
            )

    except Exception as e:
        log.error(e)


def start_watchdog(http_server_fail_event):
    log.info('Starting Watchdog')
    thread = Thread(
        target=watchdog,
        args=[http_server_fail_event]
    )
    thread.start()
    log.info('Watchdog started')
    return thread


def check_http_server(connector_cls, devices, http_server, fail_event):
    if not fail_event.is_set():
        return http_server

    log.error('HTTP Server fail event fired')
    http_server.join(timeout=1)
    http_server = start_http_server(connector_cls, devices)
    fail_event.clear()
    return http_server


def connector_error_stop_daemon(daemon, http_server, watchdog):
    log.error('Could not connect to Inverter after many retries...')
    log.error('Stopping daemon')
    http_server.join(timeout=0.1)
    watchdog.join(timeout=0.1)
    daemon.terminate(SIGKILL, None)


def run_as_daemon(daemon, args):
    connector_cls = resolve_connector(args)
    devices = args['devices']
    log.info('Starting Godenerg as daemon')
    http_server_fail_event = Event()

    try:
        http_server = start_http_server(connector_cls, devices)
        start_watchdog(http_server_fail_event)

        while True:
            http_server = check_http_server(
                connector_cls, devices, http_server, http_server_fail_event
            )
            sleep(1)
    except Exception as e:
        log.error(e)


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
