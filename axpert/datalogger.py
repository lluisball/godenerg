from sqlite3 import connect
from time import sleep
from datetime import datetime
from json import dumps as json_dumps

from axpert.settings import datalogger_conf


DT_FORMAT = '%Y%m%d%H%M%S'

COLS = [
    ('datetime', 'INTEGER'),
    ('grid_volt', 'REAL'),
    ('grid_freq', 'REAL'),
    ('ac_volt', 'REAL'),
    ('ac_freq', 'REAL'),
    ('ac_va', 'INTEGER'),
    ('ac_watt', 'INTEGER'),
    ('load_percent', 'INTEGER'),
    ('bus_volt', 'INTEGER'),
    ('batt_volt', 'REAL'),
    ('batt_charge_amps', 'INTEGER'),
    ('batt_capacity', 'INTEGER'),
    ('temp', 'INTEGER'),
    ('pv_amps', 'INTEGER'),
    ('pv_volts', 'REAL'),
    ('batt_volt_scc', 'REAL'),
    ('batt_discharge_amps', 'INTEGER'),
    ('raw_status', 'TEXT'),
    ('mask_b', 'TEXT'),
    ('mask_c', 'TEXT'),
    ('pv_watts', 'INTEGER'),
    ('mask_d', 'TEXT'),
    ('mode', 'TEXT')
]

CREATE_DB_STATEMENT = 'CREATE TABLE stats ({})'
EXPECTED_TABLES = ('stats', )


def ensure_db_structure(log, db_conn):
    query = "SELECT name FROM sqlite_master WHERE type='table'"
    table_names = [row[0] for row in db_conn.cursor().execute(query)]
    if not set(EXPECTED_TABLES) - set(table_names):
        log.debug('No difference in tables, not recreating')
        return

    log.info('Tables not found, creating database structure')
    cursor = db_conn.cursor()
    cursor.execute(
        CREATE_DB_STATEMENT.format(
           ', '.join('{} {}'.format(*item) for item in COLS)
        )
    )
    db_conn.commit()
    log.info('Database structure created')


def save_datapoint(log, db_conn, data):

    def _clean_val(val):
        if not val or val=='NA':
            return 0
        else:
            return val

    try:
        cursor = db_conn.cursor()
        log.debug('Saving datapoint')
        data['datetime'] = int(datetime.now().strftime(DT_FORMAT))
        column_values = [_clean_val(data[col_name]) for col_name, _ in COLS]
        column_vars = ', '.join('?' for _ in range(len(COLS)))
        statement = 'INSERT INTO stats VALUES ({})'.format(column_vars)
        log.debug(column_values)
        cursor.execute(statement, column_values)
        db_conn.commit()
    except Exception as e:
        log.error('Error saving datapoint')
        log.exception(e)

def datalogger_create(log, comms_executor, cmds):

    def _execute_cmd(cmd):
        response = comms_executor(cmd)
        return cmd.json(response.data, serialize=False)

    try:
        INTERVAL = datalogger_conf['interval']
        status_cmd, mode_cmd = cmds['status'], cmds['operation_mode']

        with connect(datalogger_conf['db_filename']) as db_conn:
            ensure_db_structure(log, db_conn)

            while True:
                save_datapoint(
                    log, db_conn,
                    {**_execute_cmd(status_cmd), **_execute_cmd(mode_cmd)}
                )
                sleep(INTERVAL)

    except Exception as e:
        log.error('Exception in datalogger')
        log.exception(e)

def get_range(from_dt, to_dt, extract_cols=None, as_json=False):

    def _process_rows(rows):
        return json_dumps(rows) if as_json else '\n'.join(rows)

    def _process_cols(cols):
        txt_cols = (str(col) for col in cols)
        return txt_cols if as_json else ';'.join(txt_cols)

    extract_cols = '*' if not extract_cols              \
                   else ', '.join(extract_cols)
    query = '''
        SELECT {} FROM stats
        WHERE datetime >= :from_dt AND datetime <= :to_dt
    '''.format(extract_cols)

    with connect(datalogger_conf['db_filename']) as db_conn:
        cursor = db_conn.cursor()
        cursor.execute(query, dict(from_dt=from_dt, to_dt=to_dt))
        return _process_rows(
            _process_cols(row) for row in cursor.fetchall()
        )
