from hid import Device

from connector import (Connector, IMPLEMENT)


class USBConnector(Connector):
    def write(self, data):
        self.dev.write(data)

    def read(self, size):
        return self.dev.read(size)

    def open(self):
        for device in self.devices:
            try:
                self.dev = Device(path=device)
                return
            except ValueError:
                pass

    def close(self):
        self.dev.close()
