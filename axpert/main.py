import logging
import os
import sys
import daemon

from urllib.request import urlopen
from urllib.error import HTTPError
from functools import partial
from time import sleep
from signal import SIGKILL
from threading import Thread, Lock, Event
from datetime import datetime


curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path:
    sys.path.append(root_dir)

from axpert.settings import http_conf, logger_conf, datalogger_conf
from axpert.connector import resolve_connector                  # noqa
from axpert.cmd_parser import parse_args                        # noqa
from axpert.http_handler import http_server_create              # noqa
from axpert.protocol import (CMD_REL, execute, Status)          # noqa
from axpert.datalogger import (
    datalogger_create, get_range, DT_FORMAT
)                                                               # noqa


WATCHDOG_URL = 'http://localhost:{}/cmds?cmd=operation_mode'.format(
    http_conf['port']
)
WATCHDOG_MAX_TIMEOUT = 10
WATCHDOG_INTERVAL = 10


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


def start_http_server(stop_event, comms_executor):
    log.info('Starting HTTP server')
    thread = Thread(
        target=http_server_create,
        args=[log, stop_event, comms_executor]
    )
    thread.start()
    log.info('HTTP server started')
    return thread


def start_process_executer(connector, cmd):
    log.info('Starting process executer')
    log.info('Started process executer')


def start_data_logger(comms_executor):
    log.info('Starting data logger')
    thread = Thread(
        target=datalogger_create,
        args=[log, comms_executor, CMD_REL]
    )
    thread.start()
    log.info('Started data logger')
    return thread


def atomic_execute(comms_lock, connector_cls, devices, cmd):
    try:
        comms_lock.acquire()
        with connector_cls(devices=devices, log=log) as connector:
            return execute(log, connector, cmd)
    finally:
        comms_lock.release()

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


def check_http_server(comms_executor, http_server, fail_event, stop_event):
    if not fail_event.is_set():
        return http_server

    log.error('HTTP Server fail event fired')
    stop_event.set()
    while stop_event.is_set():
        sleep(0.25)
    http_server = start_http_server(stop_event, comms_executor)
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
    http_server_stop_event = Event()
    comms_lock = Lock()
    try:
        comms_executor = partial(atomic_execute, comms_lock, connector_cls, devices)
        http_server = start_http_server(http_server_stop_event, comms_executor)

        start_data_logger(comms_executor)
        start_watchdog(http_server_fail_event)

        while True:
            http_server = check_http_server(
                comms_executor, http_server, http_server_fail_event,
                http_server_stop_event
            )
            sleep(1)
    except Exception as e:
        log.error(e)


def extract(args):

    def _get_dt(dt):
        original_dt = datetime.strptime(dt, DT_FORMAT)
        return original_dt.strftime('%Y-%m-%d %H:%M:%S')

    extract_from, extract_to = args['range'].split('-')
    extract_file = args['file']

    log.info(
        'Going to extract data from datalogger '
        'from {} to {} in format to file {}'.format(
            _get_dt(extract_from), _get_dt(extract_to), extract_file
        )
    )
    with open(extract_file, 'w') as fw:
        content = get_range(
            int(extract_from), int(extract_to),
            as_json=args['extract'] == 'json', 
            extract_cols=args['cols']
        )
        fw.write(content)

    log.info('File written successfuly')


if __name__ == '__main__':
    args = parse_args()
    log_level = logging.DEBUG if args['verbose'] else logging.INFO

    if args['daemonize']:
        with daemon.DaemonContext() as daemon:
            logging.basicConfig(
                format=logger_conf['format'],
                filename='{}/{}'.format(root_dir, logger_conf['filename'])
            )
            log = logging.getLogger('godenerg')
            log.setLevel(log_level)
            run_as_daemon(daemon, args)
    else:
        log = logging.getLogger('godenerg')
        log.setLevel(log_level)
        log.addHandler(logging.StreamHandler(sys.stdout))
        if 'extract' in args and args['extract']:
            extract(args)
        else:
            run_cmd(args)
