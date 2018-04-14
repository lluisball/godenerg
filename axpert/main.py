import logging
import os
import sys
import daemon

from signal import SIGKILL
from urllib.request import urlopen
from urllib.error import HTTPError
from functools import partial
from time import sleep, time
from multiprocessing import Process, Lock
from threading import Thread, Event
from datetime import datetime


curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path:
    sys.path.append(root_dir)

from axpert.settings import http_conf, logger_conf, datalogger_conf
from axpert.connector import resolve_connector                  # noqa
from axpert.cmd_parser import parse_args                        # noqa
from axpert.http_handler import http_server_create              # noqa
from axpert.charger import manual_charger                       # noqa
from axpert.protocol import (
    CMD_REL, execute, Status, Response, CmdSpec
)                                                               # noqa
from axpert.datalogger import (
    datalogger_create, get_range, DT_FORMAT,
    get_last_data_datetime, datalogger_http_server_create
)                                                               # noqa

MAX_RETRIES_FAILS = 1

WATCHDOG_URL = 'http://localhost:{}/cmds?cmd=operation_mode'.format(
    http_conf['port']
)
WATCHDOG_MAX_TIMEOUT = 20
WATCHDOG_INTERVAL = 40
MAX_CONNECTOR_ACQUIRE_TIME = 10

CMDS_CACHE = {}

class ShutdownDaemonAndRestart(Exception):
    pass


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


def start_http_server(comms_executor):
    log.info('Starting HTTP server')
    process = Process(
        target=http_server_create,
        args=[log, comms_executor]
    )
    process.start()
    log.info('HTTP server started')
    return process


def start_charger(comms_executor):
    log.info('Starting charger')
    process = Process(
        target=manual_charger,
        args=[log, comms_executor]
    )
    process.start()
    log.info('Started charger')
    return process


def start_datalogger(comms_executor):
    log.info('Starting data logger')
    datalogger = Process(
        target=datalogger_create,
        args=[log, comms_executor, CMD_REL]
    )
    datalogger.start()
    log.info('Started data logger')
    return datalogger


def start_datalogger_http():
    log.info('Starting data logger HTTP Server')
    datalogger_http = Process(
        target=datalogger_http_server_create,
        args=[log]
    )
    datalogger_http.start()
    log.info('Started data logger HTTP Server')
    return datalogger_http


def atomic_execute(comms_lock, connector, cmd):
    now = time()
    if cmd in CMDS_CACHE ans CMDS_CACHE[cmd]['last'] > (time() - 2):
        return CMDS_CACHE[cmd]['res']

    acquired_lock = False
    try:
        acquired_lock = comms_lock.acquire(timeout=2)
        if not acquired_lock:
            return Response(status=Status.KO, data=None)
        CMDS_CACHE[cmd] = execute(log, connector, cmd)
        CMDS_CACHE['last'] = time()
    except Exception as e:
        log.exception(e)

    finally:
        if acquired_lock:
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
            log.exception(e)
    else:
        log.debug(
            'HTTP server fail event set, cannot watchdog'
            ' waiting to do http server watchdog'
        )


def watchdog_datalogger_server(fail_event):
    last_dt = get_last_data_datetime(log)
    now = datetime.now()
    delta = (now - last_dt).total_seconds()
    datalogger_interval = datalogger_conf['interval']
    if delta > (datalogger_interval * 2):
        fail_event.set()


def watchdog(http_fail_event, datalogger_fail_event):
    try:
        while True:
            sleep(WATCHDOG_INTERVAL)
            watchdog_http_server(http_fail_event)
            watchdog_datalogger_server(datalogger_fail_event)

    except Exception as e:
        log.exception(e)


def start_watchdog(http_fail_event, datalogger_fail_event):
    log.info('Starting Watchdog')
    thread = Thread(
        target=watchdog,
        args=[http_fail_event, datalogger_fail_event]
    )
    thread.start()
    log.info('Watchdog started')
    return thread


def kill_process(process, process_label):
    try:
        os.kill(process.pid, SIGKILL)
        sleep(1)
        log.error(
            '{} FORCED termination; process alive? -> {}'.format(
                process_label, process.is_alive()
            )
        )
    except Exception as e:
        log.exception(e)


def stop_process(process, process_label):
    process.terminate()
    sleep(1)
    log.error(
        '{} terminated; process alive? -> {}'.format(
            process_label, process.is_alive()
        )
    )


def check_process(process, process_start, fail_event,
                  process_label, fail_count):
    if not fail_event.is_set():
        return process, fail_count

    fail_count += 1
    if fail_count > MAX_RETRIES_FAILS:
        raise ShutdownDaemonAndRestart()

    log.error('{} fail event fired'.format(process_label))
    stop_process(process, process_label)

    if process.is_alive():
        kill_process(process, process_label)

    process = process_start()
    fail_event.clear()

    return process, fail_count


def comms(fnx):
    def _inner(*args, **kwargs):
        try:
            connector_cls = resolve_connector(args[1])
            devices = args[1]['devices']
            with connector_cls(devices=args[1]['devices'], log=log) as connector:
                kwargs['connector'] = connector
                fnx(*args, **kwargs)
        except Exception as e:
            log.error("Connection to inverter failed")
            log.exception(e)
    return _inner


@comms
def run_as_daemon(daemon, args, connector=None):
    log.info('Starting Godenerg as daemon')
    http_server_fail_event = Event()        # Thread Event
    datalogger_server_fail_event = Event()  # Thread Event
    comms_lock = Lock()                     # Process Lock
    try:
        comms_executor = partial(
            atomic_execute, comms_lock, connector
        )

        # The starters are passed later on to the process checker
        # I curry the started calls to be able to have a generic
        # process checker that know nothing about the start parameters
        # (see check_process fnx)
        http_server_start = partial(start_http_server, comms_executor)
        datalogger_server_start = partial(start_datalogger, comms_executor)
        datalogger_http_server_start = partial(start_datalogger_http)
        charger_start = partial(start_charger, comms_executor)

        http_server = http_server_start()
        datalogger_server = datalogger_server_start()
        datalogger_http_server = datalogger_http_server_start()
        charger = charger_start()

        start_watchdog(
            http_server_fail_event, datalogger_server_fail_event
        )

        restart_count_http, restart_count_datalogger = 0, 0
        while True:
            http_server, restart_count_http = check_process(
                http_server, http_server_start, http_server_fail_event,
                'HTTP Server', restart_count_http
            )
            datalogger_server, restart_count_datalogger = check_process(
                datalogger_server, datalogger_server_start,
                datalogger_server_fail_event,
                'Datalogger Server', restart_count_datalogger
            )
            sleep(1)

    except ShutdownDaemonAndRestart:
        kill_process(http_server, 'HTTP Server')
        kill_process(datalogger_server, 'Datalogger Server')
        kill_process(datalogger_http_server, 'Datalogger HTTP Server')
        kill_process(charger, 'Charger')
        log.error('Restart all Locks, Events and Processes')

    except Exception as e:
        log.exception(e)


def extract(args):

    def _get_dt(dt):
        out_formats = {
            8: '%Y-%m-%d', 10: '%Y-%m-%d %H',
            12: '%Y-%m-%d %H:%M', 14: '%Y-%m-%d %H:%M:%S'
        }
        in_formats = {
            8: '%Y%m%d', 10:'%Y%m%d%H',
            12: '%Y%m%d%H%M', 14: '%Y%m%d%H%M%S'
        }
        original_dt = datetime.strptime(dt, in_formats[len(dt)])
        return original_dt.strftime(out_formats[len(dt)])

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
            extract_from, extract_to, as_json=args['extract'] == 'json',
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
            while True:
                run_as_daemon(daemon, args)
                sleep(5)
    else:
        log = logging.getLogger('godenerg')
        log.setLevel(log_level)
        log.addHandler(logging.StreamHandler(sys.stdout))
        if 'extract' in args and args['extract']:
            extract(args)
        else:
            run_cmd(args)
