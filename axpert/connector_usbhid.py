import hidraw

from connector import (Connector)
from time import sleep

MAX_RETRIES = 3 
NOT_OPENED = 'not open'

class USBConnector(Connector):

    def write(self, data):
        self.dev.write(data)

    def read(self, size):
        retry=0
        while retry < MAX_RETRIES:
            try:
                return self._read(size)
            except ValueError as ve:
                if str(ve)==NOT_OPENED:
                    retry += 1
                    try:
                        self.close()
                        self.open()
                    finally:
                        self.log.error("NOT OPEN in read, retry")
                else:
                    self.log.error(str(ve))
                    raise ve

    def _read(self, size):
        data = ''
        while True:
            data += ''.join(map(chr, self.dev.read(size)))
            if not data or '\r' in data or len(data) >= size:
                break
        return data

    def open(self):
        device = self.devices[0]
        try:
            self.dev = hidraw.device()
            self.dev.open_path(device.encode())
        except Exception as e:
            self.log.error(e)

    def close(self):
        self.dev.close()
