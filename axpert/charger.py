from time import sleep
from datetime import datetime, timedelta

from axpert.protocol import (
    CMD_REL, parse_inverter_conf, empty_inverter_conf
)
from axpert.settings import charger_conf
from axpert.datalogger import get_avg_last

FLOAT_VOL = charger_conf['float_voltage']
ABSORB_VOL = charger_conf['absorbtion_voltage']
ABSORB_AMPS_THRESHOLD = charger_conf['absorbtion_amps_threshold']

CHARGE_START_CHECK = charger_conf['charge_check_start']
CHARGE_END_CHECK = charger_conf['charge_check_end']


def get_inverter_conf(executor):
    try:
        response = executor(CMD_REL.get('settings'))
        return parse_inverter_conf(response.data)
    except:
        return empty_inverter_conf()


def set_float_volts_to(log, executor, target):
    try:
        log.info('Changing float charge setting to %.1f' % target)
        executor(CmdSpec(code='PBFT', size=11, val='%.1f'% target, json=None))
    except Exception as e:
        log.error('Could not set the float charge setting')
        log.exception(e)


def manual_charger(log, executor):

    def _stop_charge_check(now):
        if now.hour in range(CHARGE_START_CHECK, CHARGE_END_CHECK + 1)  \
                and now.minute in [1, 10, 20, 30, 40, 50]               \
                and second in [1, 15, 30, 45]:

            inverter_conf = get_inverter_conf()
            if not inverter_conf.float_volt \
                    or inverter_conf.float_volt == FLOAT_VOL:
                return

            avg_last_batt_volts, avg_last_batt_amps = get_avg_last(
                log, minutes
            )
            if (ABSORB_VOL - 0.25) < avg_last_batt_volts < (ABSORB_VOL + 0.25)\
                    and avg_last_batt_amps < ABSORB_AMPS_THRESHOLD:
                set_float_volts_to(log, executor, FLOAT_VOL)

    def _start_charge_check(now):
        if now.hour in [3, 4]                                       \
                and now.minute in [1, 3]                            \
                and second in [1, 10, 20]:
            inverter_conf = get_inverter_conf()
            if inverter_conf.float_volt                             \
                    and inverter_conf.float_volt == FLOAT_VOL:
                set_float_volts_to(log, executor, ABSORB_VOL)

    while True:
        now = datetime.now()
        try:
            _start_charge_check(now)
            _stop_charge_check(now)
        except Exception as e:
            log.error('Error in charger!')
            log.error(e)
        finally:
            sleep(1)
