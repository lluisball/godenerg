from sqlite3 import connect
from time import sleep
from datetime import datetime
from json import dumps as json_dumps

from settings import datalogger_conf


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


def ensure_db_structure(db_conn):
    query = "SELECT name FROM sqlite_master WHERE type='table'"
    table_names = [row[0] for row in db_conn.cursor().execute(query)]
    diff = set(EXPECTED_TABLES) - set(table_names)
    if not diff:
        return

    cursor = db_conn.cursor()
    cursor.execute(
        CREATE_DB_STATEMENT.format(
           ', '.join('{} {}'.format(*item) for item in COLS)
        )
    )
    db_conn.commit()


def save_datapoint(cursor, data):
    data['datetime'] = int(datetime.now().strftime(DT_FORMAT))
    column_values = [data[col_name] for col_name, _ in COLS]
    column_vars = ', '.join('?' for _ in range(len(COLS)))
    statement = 'INSERT INTO stats VALUES ({})'.format(column_vars)
    cursor.execute(statement, column_values)


def datalogger_create(log, comms_executor, cmds):

    def _execute_cmd(cmd):
        return cmd.json(
            comms_executor(cmd).data, serialize=False
        )

    INTERVAL = datalogger_conf['interval']
    status_cmd, mode_cmd = cmds['status'], cmds['operation_mode']

    with connect(datalogger_conf['db_filename']) as db_conn:
        ensure_db_structure(db_conn)

        while True:
            save_datapoint(
                db_conn.cursor(),
                {**_execute_cmd(status_cmd), **_execute_cmd(mode_cmd)}
            )
            db_conn.commit()
            sleep(INTERVAL)


def get_range(from_dt, to_dt, extract_cols=None, as_json=False):

    def _process_rows(rows):
        return json_dumps(rows) if as_json else '\n'.join(rows)

    def _process_cols(cols):
        return cols if as_json else ';'.join(cols)

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


if __name__ == '__main__':
    datalogger_create(None, {'db_filename': 'test.db'}, None)
