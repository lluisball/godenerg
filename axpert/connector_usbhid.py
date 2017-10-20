import hidraw

from connector import (Connector, IMPLEMENT)


class USBConnector(Connector):
    def write(self, data):
        self.dev.write(data)

    def read(self, size):
        data = ''
        while True:
            data += ''.join(map(chr, self.dev.read(size)))
            if not data or '\r' in data or len(data)>=size:
                break
        return data

    def open(self):
        for device in self.devices:
            try:
                self.dev = hidraw.device()
                self.dev.open_path(device.encode())
                return
            except ValueError:
                pass

    def close(self):
        self.dev.close()
