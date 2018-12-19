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
        reading = True
        while reading:
            incoming = ''.join(map(chr, self.dev.read(16)))
            self.log.debug("Read character [%s]", incoming)
            for char in incoming:
                if char == '\0':
                    continue
                data += char
                if char == '\r':
                    reading = False
                    break

        self.log.debug("Read data [%s]", data)
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
