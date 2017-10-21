# godenerg
Atersa / Axpert Inverter python library / interface / tool 

So far tested on usb connections, whenever I get my hands on a usb to serial adapter
I will test on serial connections.


## cmd examples

 ### get current status values
 ```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --status 

 (000.0 00.0 230.0 50.0 0322 0221 006 425 52.80 011 100 0040 0016 100.6 52.78 00000 01110110 00 00 00844 010
 ```

 ### change float voltage to 53.0 V

 > python3 axpert/main.py --usb -d /dev/hidraw0 --cmd PBFT -v 53.0  -s 8
 ```
 (ACK
 ```

## Testing:
pytest -v --pyargs axpert
