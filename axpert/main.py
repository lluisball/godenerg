import os, sys

from struct import pack
from collections import namedtuple
from enum import IntEnum
from crc16 import crc16xmodem

curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, '..'))

if root_dir not in sys.path: # add parent dir to paths
    sys.path.append(root_dir)

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


def execute(connector, cmd, val, result_size=7):
    value = val.encode() if val else b''
    encoded_cmd = cmd.encode() + value 
    checksum = crc16xmodem(encoded_cmd)
    request = encoded_cmd + pack('>H', checksum) + '\r\n'.encode()
    connector.write(request[:8])
    connector.write(request[8:])
    data = connector.read(int(result_size))
    return Response(
        data=data,
        status=parse_response_status(data)
    )

def run_cmd(args):
    Connector = resolve_connector(args)
    with Connector(devices=args['devices']) as connector:
        response = execute(
            connector, args['cmd'], args['val'], result_size=args['size'],
        )
        if response.status == Status.OK or response.status.NN:
            print(response.data)
        elif response.status == Status.KO:
            print("\nCommand not understood by inverter:\n")
            print('-' * 40)
            print(response.data)
            print('-' * 40)


if __name__ == '__main__':
    args = parse_args()
    run_cmd(args)
