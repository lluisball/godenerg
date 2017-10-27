# godenerg
Atersa / Axpert Inverter python library / interface / tool

So far tested on usb connections, whenever I get my hands on a usb to serial adapter
I will test on serial connections.

## Testing:
pytest -v --pyargs axpert


## Run as daemon

For now this starts a http server that allows quering of commands.
The idea is for the daemon to also do datalogging and dynamic configuration
processes to bypass the crappy firmware the axpert has.

```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --deamon
```

Over the local network:

```
http://machine_ip:8889/cmds?cmd=status
```

or

```
http://machine_ip:8889/cmds?cmd=operation_mode
```

or

```
http://machine_ip:8889/cmds?cmd=operation_mode&cmd=status
```

or

```
http://machine_ip:8889/cmds?cmd=operation_mode&cmd=status&merge=1
```
(to merge the 2 json nodes into a single node)

## cmd examples

 ### Get current status values (QPIGS command)
 ```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --status

 (000.0 00.0 230.0 50.0 0322 0221 006 425 52.80 011 100 0040 0016 100.6 52.78 00000 01110110 00 00 00844 010
 ```

 ### Get current status values as JSON

 ```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --status --json

    {"ssc_firmware_updated": false, "grid_volt": 0.0, "raw_status": "01010000", "batt_volt": 49.7, "ac_volt": 229.9, "batt_capacity": 75, "configuration_changed": true, "pv_amps": 0, "bus_volt": 400.0, "ac_freq": 50.0, "ac_va": 298, "mask_d": 10, "batt_charge_amps": 0, "batt_volt_scc": 0.0, "load_status": true, "sbu_priority_version": false, "pv_volts": 0.0, "temp": 45, "load_percent": 6.0, "charge_source": ["not_charging"], "batt_discharge_amps": 5, "pv_watts": 0, "batt_volt_to_steady": false, "mask_c": 0, "grid_freq": 0.0, "mask_b": 0, "ac_watt": 241}
 ```

 ### Get operation mode (QMOD command):

```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --op-mode

```

 ### Get operation mode as json:

```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --op-mode --json

    {"mode": "BT"}
```

 ### Change Float Voltage to 53.0 V

 ```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --cmd PBFT -v 53.0  -s 8
 (ACK
 ```

 ### Change Utility MAX charge current to 10 amps for first paralel device

 ```
 > python3 axpert/main.py --usb -d /dev/hidraw0 --cmd MCHGC -v 010 -s 8 
 (ACK
 ```



