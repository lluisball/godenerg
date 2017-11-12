logger_conf = {
    'filename': 'godenerg.log',
    'format': '[%(asctime)s] %(message)s'
}

http_conf = {
    'port': 8889
}


datalogger_conf = {
    'db_filename': '/home/ups/godenerg/godenerg.db',
    'interval': 15,
    'last_interval': 2,
    'samples': 7200,
    'port': 8890
}

charger_conf = {
    'max_charge_amps': 60,
    'float_volt': 52.8,
    'absorbtion_volt': 58.4,

    'absoption_amps_threshold': 7,
    'max_absorption_time': 60 * 4,
}
