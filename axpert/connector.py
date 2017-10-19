from importlib import import_module

IMPLEMENT = 'Implement in subclass'
connector_registry = {
    'serial': 'connector_serial.ConnectorSerial',
    'usb': 'connector_usbhid'
}


class Connector(object):

    def __init__(self, devices=None):
        self.devices = devices

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def write(self, data):
        raise NotImplementedError(IMPLEMENT)

    def read(self, size):
        raise NotImplementedError(IMPLEMENT)

    def open(self):
        raise NotImplementedError(IMPLEMENT)

    def close(self):
        raise NotImplementedError(IMPLEMENT)


def resolve_connector(args):
    for option, module_namespace in connector_registry.items():
        if args[option]:
            return import_module(module_namespace)
