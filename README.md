# m365py [![][img_license]](#license) [![][img_loc]][loc] [![Build status](https://ci.appveyor.com/api/projects/status/ylk3eiuu65t028kv?svg=true)](https://ci.appveyor.com/project/AntonHakansson/m365py)
[img_license]: https://img.shields.io/badge/License-MIT_or_Apache_2.0-blue.svg
[img_loc]: https://tokei.rs/b1/github/AntonHakansson/rbreakout
[loc]: https://github.com/Aaronepower/tokei

A Python2.7 and Python3x library to receive parsed BLE Xiaomi M365 scooter(Version=V1.3.8) messages using [bluepy](https://github.com/IanHarvey/bluepy).

## Installation using pip
```console
pip install git+https://github.com/AntonHakansson/m365py.git#egg=m365py
```

## Usage
See `examples` folder for full example of all supported requests.

```python
import time
import json

from m365py import m365py
from m365py import m365message


# callback for received messages from scooter
def handle_message(m365_peripheral, m365_message, value):
    print('{} => {}'.format(m365_message._attribute, json.dumps(value, indent=4)))
    # Will print:
    # Attribute.MOTOR_INFO => {
    #   "battery_percent": 84,
    #   "speed_kmh": 0.0,
    #   "speed_average_kmh": 0.0,
    #   "odometer_km": 155.819,
    #   "trip_distance_m": 0,
    #   "uptime_s": 159,
    #   "frame_temperature": 24.0
    # }

scooter_mac_address = 'XX:XX:XX:XX:XX:XX'
scooter = m365py.M365(scooter_mac_address, handle_message)
scooter.connect()

scooter.request(m365message.motor_info)
time.sleep(5)

scooter.disconnect()

```

## Find MAC address for scooter

This package includes the option to scan and list nearby m365 Scooters.
Simple excecute the package as such:

```console
sudo python -m m365py
```

