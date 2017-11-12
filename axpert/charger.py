from datetime import datetime, timedelta

from axpert.protocol import CMD_REL, parse_inverter_conf
from axpert.settings import charger_conf, datalogger_conf

def get_inverter_conf(executor):
    try:
        response = executor(CMD_REL.get('settings'))
        return parse_inverter_conf(response.data)
    except:
        return None


def set_float_volts_to(log, executor, target):
    try:
        log.info('Changing float charge setting to %.1f' % target)
        executor(CmdSpec(code='PBFT', size=9, val='%.1f'% target, json=None))
    except Exception as e:
        log.error('Could not set the float charge setting')
        log.exception(e)


# def set_charger_volts(log, executor):
#    inverter_conf = 

def is_been_charged_today(log):
    pass


def charger_process(log, executor):
    
    def _day():
        return int(datetime.now().strftime('%Y%m%d'))

    charge_day = _day()
    charged_today = False

    while True:
        sleep(60)
        if charge_day < _day():
            if not is_been_charged_today():
                charged_today = False
                set_charge_volts(executor)


def manual_charger(log, executor):
    FLOAT = 52.8
    ABSORP = 58.4

    def _stop_charge_check(now):
        if now.hour in [11, 12, 13, 14, 15, 16]                     \
                and now.minute in [1, 10, 20, 30, 40, 50]           \
                and second in [1, 10, 20]:
            inverter_conf = get_inverter_conf() 
            if inverter_conf.float_volt > FLOAT:
                avg_last_batt_volts, avg_last_batt_amps = get_avg_last()
                if (ABSORP - 0.5) < avg_last_batt_volts < (ABSORP + 0.5) \ 
                        and avg_last_batt_amps < 7.1:
                    set_float_volts_to(log, executor, FLOAT)

    def _start_charge_check(now):
        if now.hour=5 and now.minute in [1, 3] and second in [1, 10, 20]:
            inverter_conf = get_inverter_conf() 
            if inverter_conf.float_volt == FLOAT:
                set_float_volts_to(log, executor, ABSORP)

    while True:
        now = datetime.now()
        _start_charge_check(now)
        _stop_charge_check(now)
        sleep(1)

