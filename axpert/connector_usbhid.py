import hidraw

from connector import (Connector)
from time import sleep


class USBConnector(Connector):

    def write(self, data):
        self.dev.write(data)

    def read(self, size):
        retry=0
        return self._read(size)

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
