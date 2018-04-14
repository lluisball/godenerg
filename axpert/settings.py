APP_PATH = '/home/pi/godenerg/'


logger_conf = {
    'filename': 'godenerg.log',
    'format': '[%(asctime)s] %(message)s'
}

http_conf = {
    'port': 8889
}


datalogger_conf = {
    'db_filename': APP_PATH + 'godenerg.db',
    'interval': 15,
    'last_interval': 2,
    'samples': 7200,
    'port': 8890
}

charger_conf = {
    'float_voltage': 52.8,
    'absorbtion_voltage': 58.4,
    'absorbtion_amps_threshold': 6.4,
    'charge_check_start': 11,
    'charge_check_end': 23
}

weather_api_conf = {
    'enable': True,
    'url': 'http://api.apixu.com/v1/forecast.json?'\
           'key={APIXU_API_KEY}&q={LAT},{LNG}&days=4',
    'lat': '39.5946187',
    'lng': '2.9024177',
    'api_key_file': APP_PATH + 'apixu_api_key.txt'
}
