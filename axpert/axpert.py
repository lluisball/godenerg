from struct import pack
from collections import namedtuple
from enum import IntEnum
from crc16 import crc16xmodem

from axpert.connector import resolve_connector
from axpert.cmd_parser import parse_args

NAK, ACK = 'NAK', 'ACK'

Response = namedtuple('Response', ['status', 'data'])


class Status(IntEnum):
    OK = 1
    KO = 2
    NN = 3


def parse_response_status(data):
    if not data or (ACK not in data and NAK not in data):
        return Status.NN
    elif ACK in data:
        return Status.OK
    elif NAK in data:
        return Status.KO


def execute(connector, cmd, result_size=7):
    checksum = crc16xmodem(cmd.encode())
    request = cmd + pack('>H', checksum) + '\r'
    connector.write(request)
    data = connector.read(result_size)
    return Response(
        data=data,
        status=parse_response_status(data)
    )

def run_cmd(args):
    Connector = resolve_connector(args)
    with Connector(devices=args['devices']) as connector:
        response = execute(
            connector, args['cmd'], result_size=args['size'],
            out_format=args['format']
        )
        if response.status == Status.OK:
            print(response.data)
        elif response.status == Status.KO:
            print("\nCommand not understood by inverter:\n")
            print('-' * 40)
            print(response.data)
            print('-' * 40)
        elif response.status == Status.NN:
            print("\nUnknown error, no data was returned\n")


if __name__ == '__main__':
    args = parse_args()
    run_cmd(args)
