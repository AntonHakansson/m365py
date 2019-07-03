# m365py
A python3 library to receive parsed BLE Xiaomi M365 scooter(Version=V1.3.8) messages using bluepy.


## Installation using pip
```bash
pip install git+https://github.com/AntonHakansson/m365py.git#egg=m365py
```

## Usage
See `examples` folders for full example of all supported requests.

```python
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

scooter_mac_address = 'D6:0E:DB:7B:EA:AB'
scooter = m365py.M365(scooter_mac_address, handle_message)
scooter.connect()

scooter.request(m365message.motor_info)
time.sleep(5)

scooter.disconnect()

```

