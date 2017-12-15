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
    'float_voltage': 52.8,
    'absorbtion_voltage': 58.4,
    'absorbtion_amps_threshold': 6.8,
    'charge_check_start': 11,
    'charge_check_end': 23
}
