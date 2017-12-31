from urllib.request import urlopen

from socket import timeout
from json import loads, JSONDecodeError
from datetime import date, timedelta, datetime
from os.path import isfile
from os import rename

from axpert.settings import weather_api_conf, APP_PATH

LAST_LOG = APP_PATH + '.last_forecast'
LAST_REPORT = APP_PATH + 'weather.json'

MAX_WEATHER_REPORT_WAIT = 10
FORMAT = '%Y-%m-%d %I'

WEEKDAYS = {
    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday',
    3: 'Thursday', 4: 'Friday', 5: 'Saturday',
    6: 'Sunday'
}

TWILIGHT_OFFSET_MINS = 60

MOON, SUNNY, PARTLY_SUNNY, CLOUDY= -1, 0, 1, 2
OVERCAST, RAIN, HEAVY_RAIN, STORM  =  3, 4, 5, 6

EXTRA_BAD_WEATHER = 1

weather_condition_match = {
    'clear' : MOON,
    'sunny' : SUNNY,
    'partly cloudy': PARTLY_SUNNY,
    'cloudy': CLOUDY,
    'overcast': OVERCAST,
    'mist': CLOUDY,
    'fog': CLOUDY
}

weather_condition_rules = {
    'rain': RAIN,
    'heavy': EXTRA_BAD_WEATHER,
    'sleet': RAIN,
    'ice': RAIN,
    'snow': RAIN,
    'torrential': EXTRA_BAD_WEATHER,
    "thundery outbreaks in nearby": EXTRA_BAD_WEATHER,
    "blizzard": RAIN
}


def weather_condition_to_code(condition):
    condition = condition.lower()
    code_match = weather_condition_match.get(condition)
    if code_match:
        return code_match

    code = 0
    for txt, adder in weather_condition_rules.items():
        if txt in condition:
            code += adder

    if code > STORM:
        code = STORM

    return code


def calculate_sun_hours(data, from_now=False):
    FORMAT = '%I:%M %p'
    sunrise = datetime.strptime(data['astro']['sunrise'], FORMAT)
    sunset = datetime.strptime(data['astro']['sunset'], FORMAT)

    if from_now:
        start_sun = datetime.strptime(datetime.now().strftime(FORMAT), FORMAT)
    else:
        start_sun = sunrise + timedelta(minutes=TWILIGHT_OFFSET_MINS)

    end_sun = sunset - timedelta(minutes=TWILIGHT_OFFSET_MINS)
    return {
        'start_sun': start_sun,
        'end_sun': end_sun,
        'hours': int((end_sun - start_sun).total_seconds() / 60.0 / 60.0)
    }


def calculate_cloud_cover(data, all_day=False):
    now = datetime.now()
    sun_hours = calculate_sun_hours(data)
    if not all_day:
        from_hour = now.hour
    else:
        from_hour = sun_hours['start_sun'].hour

    to_hour = sun_hours['end_sun'].hour
    hours = data['hour'][from_hour: to_hour + 1]
    total_cover = sum(hour['cloud'] for hour in hours)

    if total_cover > 0:
        return int(float(total_cover) / float(len(hours)))
    else:
        return 0


def calculate_today_forecast(data):
    now = datetime.now()
    sun_hours = calculate_sun_hours(data)
    from_hour = now.hour
    to_hour = sun_hours['end_sun'].hour

    hours = data['hour'][from_hour: to_hour + 1]

    forecast_code = MOON
    for hour_forecast in hours:
        hour_code = weather_condition_to_code(
            hour_forecast['condition']['text']
        )
        if forecast_code < hour_code:
            forecast_code = hour_code

    return forecast_code


def build_api_call_url():
    with open(weather_api_conf['api_key_file'], 'r') as fkey:
        api_key = fkey.read().strip()
        return weather_api_conf['url'].format(
            APIXU_API_KEY=api_key, LAT=weather_api_conf['lat'],
            LNG=weather_api_conf['lng']
        )


def last_json_report():
    with open(LAST_REPORT, 'r') as f:
        return loads(f.read())


def get_last_requested_log():
    with open(LAST_LOG, 'r') as f:
        return f.read()


def set_last_requested_log(now):
    with open(LAST_LOG, 'w') as f:
        f.write(now)


def json_parse_error(fnx):
    def _inner(log):
        try:
            return fnx(log)
        except JSONDecodeError as jde:
            log.error('Can not decode the JSON from weather service')
            log.exception(jde)
            return None
    return _inner


@json_parse_error
def get_last_forecast(log):
    now = datetime.now().strftime(FORMAT)
    last = '-' if not isfile(LAST_LOG) else get_last_requested_log()

    if last == now and isfile(LAST_REPORT):
        return last_json_report()

    with open(LAST_REPORT + 'tmp', 'w') as f:
        try:
            url = build_api_call_url()
            response = urlopen(
                url, timeout=MAX_WEATHER_REPORT_WAIT
            )
            log.info('http call to weather service done')
            data = response.read()
            f.write(data.decode())

        except Exception as e:
            if isfile(LAST_LOG):
                # leave for an extra hour and return last report
                return last_json_report()
            log.error(
                'Can not get weather API data, timed out or http error, URL:'
            )
            log.error(build_api_call_url())
            log.exception(e)
            return None

    rename(LAST_REPORT + 'tmp', LAST_REPORT)
    set_last_requested_log(now)
    return loads(data.decode())


def days_labels():
    today = date.today()
    return {
        'today_label': WEEKDAYS[today.weekday()],
        'day_1_label': WEEKDAYS[(today + timedelta(days=1)).weekday()],
        'day_2_label': WEEKDAYS[(today + timedelta(days=2)).weekday()],
        'day_3_label': WEEKDAYS[(today + timedelta(days=3)).weekday()],
   }


def get_weather_stats(log):
    data  = get_last_forecast(log)
    if not data:
        return None

    now_text = data['current']['condition']['text']
    forecast = data['forecast']['forecastday']
    day_1_text = forecast[1]['day']['condition']['text']
    day_2_text = forecast[2]['day']['condition']['text']
    day_3_text = forecast[3]['day']['condition']['text']

    return {
        'temp': data['current']['temp_c'],
        'humd': data['current']['humidity'],
        'now_txt': now_text,
        'now_code': weather_condition_to_code(now_text),
        'today_code': calculate_today_forecast(forecast[0]),
        'today_cloud_cover': calculate_cloud_cover(forecast[0]),
        'day_1_txt': day_1_text,
        'day_2_txt': day_2_text,
        'day_3_txt': day_3_text,
        'day_1_code': weather_condition_to_code(day_1_text),
        'day_2_code': weather_condition_to_code(day_2_text),
        'day_3_code': weather_condition_to_code(day_3_text),
        'today_txt': forecast[0]['day']['condition']['text'],
        **days_labels()
    }
