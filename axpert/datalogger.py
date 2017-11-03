from http.server import HTTPServer
from sqlite3 import connect
from time import sleep
from datetime import datetime
from json import dumps as json_dumps
from math import ceil
from pygal import Line 
from pygal.style import Style
from functools import reduce

from axpert.settings import datalogger_conf
from axpert.http_handler import (
    BaseGodenergHandler, html_response
)

DT_FORMAT = '%Y%m%d%H%M%S'
INTERVAL = datalogger_conf['interval']

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
    try:
        cursor = db_conn.cursor()
        log.debug('Saving datapoint')
        data['datetime'] = int(datetime.now().timestamp())
        column_values = [data[col_name] for col_name, _ in COLS]
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
        status_cmd, mode_cmd = cmds['status'], cmds['operation_mode']

        with connect(datalogger_conf['db_filename']) as db_conn:
            ensure_db_structure(log, db_conn)

            while True:
                status_data = _execute_cmd(status_cmd) 
                mode_data = _execute_cmd(mode_cmd)
                if status_data and mode_data:
                    save_datapoint(
                        log, db_conn, {**status_data, **mode_data}
                    )
                sleep(INTERVAL)

    except Exception as e:
        log.error('Exception in datalogger')
        log.exception(e)


def txt_dt_to_int(txt):
    txt_dt = txt + ((14 - len(txt)) * '0') 
    return int(datetime.strptime(txt_dt, DT_FORMAT).timestamp())


def get_last_data_datetime(log):
    with connect(datalogger_conf['db_filename']) as db_conn:
        cursor = db_conn.cursor()
        cursor.execute(
            'SELECT datetime FROM stats ORDER BY datetime DESC LIMIT 1' 
        )
        dt = cursor.fetchone()
        if dt:
            try:
                return datetime.fromtimestamp(dt[0])  
            except Exception as e:
                log.exception(e)
                return 0
        else:
            return 0 


def get_range(from_dt, to_dt, extract_cols=None,
              as_json=False, raw_data=False, grouped=False):

    MAX_GROUPED_ITEMS = 2048
    
    def _build_query(db_conn, params):
        cols_stat = '*' if not extract_cols  else ', '.join(extract_cols)

        where_stat = 'WHERE datetime >= :from_dt AND datetime <= :to_dt'
        if not grouped:
            return 'SELECT {} FROM stats {}'.format(cols_stat, where_stat)

        total_items, = db_conn.cursor().execute(
            'SELECT COUNT(1) FROM stats ' + where_stat, params
        ).fetchone()

        if total_items <= MAX_GROUPED_ITEMS:
            return 'SELECT 1, datetime, {} FROM stats {}'.format(
                cols_stat, where_stat
            )

        return '''
            SELECT {group_coe}, (datetime / {group_coe}), {cols} 
            FROM stats {where_stat} GROUP BY (datetime / {group_coe}) 
        '''.format(
                **dict(
                    group_coe=INTERVAL * ceil(total_items / MAX_GROUPED_ITEMS),
                    cols=','.join('AVG({})'.format(c) for c in extract_cols),
                    where_stat=where_stat
                )
            )
                
    def _process_rows(rows):
        return json_dumps(rows) if as_json else '\n'.join(rows)

    def _process_cols(cols):
        txt_cols = (str(col) for col in cols)
        return txt_cols if as_json else ';'.join(txt_cols)


    with connect(datalogger_conf['db_filename']) as db_conn:
        params = dict(
            from_dt=txt_dt_to_int(from_dt), to_dt=txt_dt_to_int(to_dt)
        )
        cursor = db_conn.cursor()
        cursor.execute(_build_query(db_conn, params), params) 
        if raw_data:
            return cursor.fetchall()

        return _process_rows(
            _process_cols(row) for row in cursor.fetchall()
        )


def datalogger_http_server_create(log):
    http_handler = create_base_datalogger_handler(log)
    server = HTTPServer(('', datalogger_conf['port']), http_handler)
    server.serve_forever()

def create_base_datalogger_handler(log):

    class DataLoggerHandler(BaseDataLoggerHandler):

        def __init__(self, *args, **kwargs):
            self.log = log
            super(DataLoggerHandler, self).__init__(*args, **kwargs)

    return DataLoggerHandler


class BaseDataLoggerHandler(BaseGodenergHandler):

    routes = {
        '/graph': 'plot_datalogger' 
    }

    MAX_X_LABELS = 20
    MAX_Y_LABELS = 20

    def compose_chart_data(self, data, secondary=False):
        datalen = len(data)
        label_mod = ceil(datalen / self.MAX_X_LABELS) \
            if datalen > self.MAX_X_LABELS else None 

        def _fold_data_point(points, point):
            if secondary:
                index, (coef, tms, val_1, val_2) = point
            else:
                index, (coef, tms, val_1) = point

            if label_mod and (index % label_mod) == 0:
                points['labels'].append(
                    datetime.fromtimestamp(int(tms * coef))
                )
            else:
                points['labels'].append('')

            points['values_1'].append(val_1)
            if secondary:
                points['values_2'].append(val_2)
            return points
    
        return reduce(
            _fold_data_point, enumerate(data), 
            dict(labels=[], values_1=[], values_2=[])
        )
        
    def resolve_y_labels(self, items):
        itemlen = len(items)
        if itemlen <= self.MAX_Y_LABELS:
            return items

        step = ceil(itemlen / self.MAX_Y_LABELS)
        return items[::step]

    @staticmethod
    def custom_style(col_2):
        return Style(
            foreground='#000000',
            foreground_strong='#FFA500' if col_2 else '#333333',
            foreground_subtle='#630C0D',
            opacity='.7',
            opacity_hover='.9',
            transition='400ms ease-in',
            colors=('#3333FF', '#33FF33')
        ) 

    @staticmethod
    def create_range(data, col_index):
        return (
            int(min(data, key=lambda i: i[col_index])[col_index]), 
            int(max(data, key=lambda i: i[col_index])[col_index])
        )

    def build_line(self, data, col_2):
        COL_1_INDEX, COL_2_INDEX = 2, 3
        
        range_1_from, range_1_to = \
            BaseDataLoggerHandler.create_range(data, COL_1_INDEX)

        if col_2:
            range_2_from, range_2_to = \
                BaseDataLoggerHandler.create_range(data, COL_2_INDEX)

        chart = Line(
            show_dots=False, fill=False if col_2 else True, 
            show_x_guides=False, show_y_guides=True, 
            range=(range_1_from, range_1_to),
            secondary_range=(range_2_from, range_2_to) if col_2 else None,
            x_label_rotation=40, title='Inverter Stats',
            style=BaseDataLoggerHandler.custom_style(col_2)
        )
        chart.y_labels = self.resolve_y_labels(
            range(range_1_from, range_1_to + 1)
        )
        return chart

    @html_response
    def plot_datalogger(self, req):
        from_dt = req['from'][0]
        to_dt = req['to'][0]
        col_1 = req['col_1'][0]
        col_2 = req.get('col_2', [None])[0]
        cols = [col for col in [col_1, col_2] if col]

        data = get_range(
            from_dt, to_dt, cols, raw_data=True, grouped=True,
        )

        line_chart = self.build_line(data, col_2)

        chart_data = self.compose_chart_data(
            data, secondary=(col_2!=None)
        )
        line_chart.add(col_1[:11], chart_data['values_1'])
        if col_2:
            line_chart.add(col_2[:11], chart_data['values_2'], secondary=True)

        line_chart.x_labels = chart_data['labels'] 
        return line_chart.render()
