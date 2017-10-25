from importlib import import_module

IMPLEMENT = 'Implement in subclass'
connector_registry = {
    'serial': 'axpert.connector_serial.ConnectorSerial',
    'usb': 'axpert.connector_usbhid.USBConnector'
}


class Connector(object):

    def __init__(self, devices=None, log=None):
        self.devices = devices
        self.log = log

    def __enter__(self):
        self.log.debug('Opening device...')
        self.open()
        self.log.debug('Device opened!')
        return self

    def __exit__(self, *args):
        self.log.debug('Closing device...')
        self.close()
        self.log.debug('Device closed!')

    def write(self, data):
        raise NotImplementedError(IMPLEMENT)

    def read(self, size):
        raise NotImplementedError(IMPLEMENT)

    def open(self):
        raise NotImplementedError(IMPLEMENT)

    def close(self):
        raise NotImplementedError(IMPLEMENT)


def resolve_connector(args):
    for option, cls_namespace in connector_registry.items():
        if option in args and args[option]:
            tokens = cls_namespace.split('.')
            module_path, cls_name = '.'.join(tokens[:-1]), tokens[-1]
            module = import_module(module_path)
            return getattr(module, cls_name)
