from time import sleep
from serial import (Serial, SerialException)
from axpert.connector import Connector


MAX_CONNECT_RETRIES = 5
SLEEP_BETWEEN_RETRIES = 5


def serial_reconnecter(fnx):

    def __inner__(*args, **kwargs):
        for retry in range(MAX_CONNECT_RETRIES):
            self = args[0]
            try:
                if not self.serial:
                    raise TypeError()
                return fnx(*args, **kwargs)
            except TypeError as e:
                # Serial operation can raise type error on
                # connection lost, try reconnecting after
                # sleeping for a bit
                sleep(SLEEP_BETWEEN_RETRIES)
        print(
            '\n[SerialConnector] Could not connect to the device'
            ' trough specified devices/s %s' % ', '.join(self.devices)
        )
        exit(1)

    return __inner__


class SerialConnector(Connector):

    @serial_reconnecter
    def write(self, data):
        self.serial.write(data)
        self.serial.flush()

    @serial_reconnecter
    def read(self, size):
        try:
            return self.serial.read(size)
        except SerialException as e:
            return None

    def open(self):
        for port in self.devices:
            serial = Serial(port, 2400, timeout=1, rtscts=False)
            if serial:
                self.serial = serial
                return

    def close(self):
        self.serial.close()
