from connector import (Connector, IMPLEMENT)


class USBConnector(Connector):
    def write(self, data):
        raise NotImplementedError(IMPLEMENT)

    def read(self, size):
        raise NotImplementedError(IMPLEMENT)

    def open(self):
        raise NotImplementedError(IMPLEMENT)

    def close(self):
        raise NotImplementedError(IMPLEMENT)
