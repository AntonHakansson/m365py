from typing import Callable, Iterable, Optional
from enum import Enum
import struct
import time
import json
import logging

from bluepy.btle import Peripheral, Characteristic, UUID, DefaultDelegate, ADDR_TYPE_RANDOM

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)

log = logging.getLogger('m365py')
log.setLevel(logging.DEBUG)
log.addHandler(stream_handler)

class MessageBuilder:
    def __init__(self):
        self._checksum = 0
        self._direction = 0
        self._read_write = 0
        self._position = 0
        self._payload = []

    def direction(self, direction):
        direction = direction.value.to_bytes(1, 'big')
        self._direction = int.from_bytes(direction, 'big', signed=True)
        self._checksum += self._direction
        return self

    def read_write(self, read_write):
        read_write = read_write.value.to_bytes(1, 'big')
        self._read_write = int.from_bytes(read_write, 'big', signed=True)
        self._checksum += self._read_write
        return self

    def position(self, position) :
        position = position.value.to_bytes(1, 'big')
        self._position = int.from_bytes(position, 'big', signed=True)
        self._checksum += self._position
        return self

    def payload(self, payload):
        for byte in payload:
            byte = byte.to_bytes(1, 'big')
            payload_part = int.from_bytes(byte, 'big', signed=True)
            self._payload.append(payload_part)
            self._checksum += payload_part
        self._checksum += len(payload) + 2
        return self

    def build(self):
        message = [
            int.from_bytes(b'\x55', 'big', signed=True),
            int.from_bytes(b'\xaa', 'big', signed=True)
        ]

        message.append(len(self._payload) + 2)
        message.append(self._direction)
        message.append(self._read_write)
        message.append(self._position)
        message += self._payload

        checksum = self._checksum ^ 0xffff

        message.append(int.from_bytes((checksum & 0xff).to_bytes(1, 'big'), 'big', signed=True))
        message.append(-1)
        # message.append(int.from_bytes(((checksum >> 8) & 0x000000ff).to_bytes(1, 'big', signed=False), 'big', signed=True))
        m = bytearray()
        for a in message:
            m.extend(a.to_bytes(1, 'big', signed=True))

        return m

class Message:
    class Direction(Enum):
        ODOMETER_TO_BLE   = 0x00 # ???
        BLE_TO_MOTOR      = 0x20
        #MOTOR_TO_BLE      = 0x21
        BLE_TO_BATTERY    = 0x22
        MOTOR_TO_BLE      = 0x23
        BATTERY_TO_BLE    = 0x25

    class Action(Enum):
        READ  = 0x01
        WRITE = 0x03


    class Attribute(Enum):
        ODOMETER             = 0x00 # ???
        BATTERY_INFO         = 0x31
        BATTERY_PERCENTAGE   = 0x32
        BATTERY_AMPERE       = 0x33
        BATTERY_VOLTAGE      = 0x34
        DISTANCE             = 0xB9
        SPEED                = 0xB5
        TRIP_SUPERMASTER     = 0xB0
        DISTANCE_SUPERMASTER = 0x25
        BATTERY_SUPERMASTER  = 0x31

    PAYLOAD = [0x02]
    PAYLOAD_TRIP_SUPERMASTER = [0x20]
    PAYLOAD_BATTERY_SUPERMASTER = [0x0a]

    battery_voltage = MessageBuilder() \
        .direction(Direction.BLE_TO_BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_VOLTAGE) \
        .read_write(Action.READ).build()
#    battery_voltage = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'4', b'\x02', b'\xa3', b'\xff']

    battery_ampere = MessageBuilder() \
        .direction(Direction.BLE_TO_BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_AMPERE) \
        .read_write(Action.READ).build()

#    battery_ampere = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'3', b'\x02', b'\xa4', b'\xff']

    battery_percentage = MessageBuilder() \
        .direction(Direction.BLE_TO_BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_PERCENTAGE) \
        .read_write(Action.READ).build()

#    battery_life = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'2', b'\x02', b'\xa5', b'\xff']]
    odometer = MessageBuilder() \
        .direction(Direction.BLE_TO_MOTOR) \
        .payload(PAYLOAD) \
        .position(Attribute.DISTANCE) \
        .read_write(Action.READ).build()

    speed = MessageBuilder() \
        .direction(Direction.BLE_TO_MOTOR) \
        .payload(PAYLOAD) \
        .position(Attribute.SPEED) \
        .read_write(Action.READ).build()

    trip_supermaster = MessageBuilder() \
        .direction(Direction.BLE_TO_MOTOR) \
        .payload(PAYLOAD_TRIP_SUPERMASTER) \
        .position(Attribute.TRIP_SUPERMASTER) \
        .read_write(Action.READ).build()

    distance_supermaster = MessageBuilder() \
        .direction(Direction.BLE_TO_MOTOR) \
        .payload(PAYLOAD) \
        .position(Attribute.DISTANCE_SUPERMASTER) \
        .read_write(Action.READ).build()

    battery_supermaster = MessageBuilder() \
        .direction(Direction.BLE_TO_BATTERY) \
        .payload(PAYLOAD_BATTERY_SUPERMASTER) \
        .position(Attribute.BATTERY_SUPERMASTER) \
        .read_write(Action.READ).build()


def phex(s):
    return ''.join('/x{:02x}'.format(x) for x in s)

class M365Delegate(DefaultDelegate):
    def __init__(self, m365):
        DefaultDelegate.__init__(self)
        self._m365 = m365

    def handleNotification(self, cHandle, data):
        payload = bytes(data)

        # sometimes scooter sends empty payload
        if len(payload) == 0: return
        log.debug("Notification received from {}: {}".format(cHandle, phex(data)))
        direction, attribute = struct.unpack('<xxxBxB', payload[:6])
        direction, attribute = Message.Direction(direction), Message.Attribute(attribute)

        log.debug('{}, {}'.format(Message.Direction(direction), Message.Attribute(attribute)))

        if direction == Message.Direction.BATTERY_TO_BLE:
            if attribute == Message.Attribute.BATTERY_SUPERMASTER:
                (capacity,
                  battery_percent,  # %
                  current, voltage, battery_temperature_1,
                  battery_temperature_2) = struct.unpack('<HHhHBB', payload[6:16])
                capacity /= 1000  # Ah
                current /= 100  # A
                voltage /= 100  # V
                battery_temperature_1 -= 20  # C
                battery_temperature_2 -= 20  # C

                log.debug('Got capacity: {} Ah, current: {} A, voltage: {} V, battery_temperature_1: {} C, battery_temperature_2: {} C'.format(capacity, current, voltage, battery_temperature_1, battery_temperature_2))
                self._m365.state.battery_capacity = capacity
                self._m365.state.battery_current = current
                self._m365.state.battery_voltage = voltage
                self._m365.state.battery_percent = battery_percent
                self._m365.state.battery_temperature_1 = battery_temperature_1
                self._m365.state.battery_temperature_2 = battery_temperature_2
                return

            elif attribute == Message.Attribute.BATTERY_VOLTAGE:
                (voltage,) = struct.unpack('<H', payload[6:8])
                voltage /= 100
                log.debug('Got voltage: {} V'.format(voltage))
                self._m365.state.battery_voltage = voltage
                return

            elif attribute == Message.Attribute.BATTERY_AMPERE:
                (battery_ampere,) = struct.unpack('<H', payload[6:8])
                battery_ampere /= 100
                log.debug('Got ampare: {} A'.format(battery_ampere))
                self._m365.state.battery_ampere = battery_ampere
                return

            elif attribute == Message.Attribute.BATTERY_PERCENTAGE:
                (battery_percentage,) = struct.unpack('<H', payload[6:8])
                log.debug('Got battery percentage: {} %'.format(battery_percentage))
                self._m365.state.battery_percentage = battery_percentage
                return

        elif direction == Message.Direction.MOTOR_TO_BLE:
            if attribute == Message.Attribute.TRIP_SUPERMASTER:
                (error, warning, flags, workmode,
                  battery, speed, speed_average) = struct.unpack('<HHHHHHH', payload[6:20])
                speed /= 100  # km/h
                speed_average /= 100  # km/h
                log.debug('Got speed: {} kmh, average speed: {} kmh'.format(speed, speed_average))

                self._m365.state.speed_kmh = speed
                self._m365.state.speed_average_kmh = speed_average
                return

            elif attribute == Message.Attribute.DISTANCE_SUPERMASTER:
                (distance_left,) = struct.unpack('<H', payload[6:8])
                distance_left /= 100
                log.debug('Got distance left: {} km'.format(distance_left))
                self._m365.state.distance_left_km = distance_left
                return

            elif attribute == Message.Attribute.SPEED:
                (speed,) = struct.unpack('<H', payload[6:8])
                speed /= 100
                log.debug('Got speed: {} kmh'.format(speed))
                self._m365.state.speed_kmh = speed
                return

            elif attribute == Message.Attribute.DISTANCE:
                (odometer,) = struct.unpack('<H', payload[6:8])
                odometer_km = odometer / 1000
                log.debug('Got odometer: {} km'.format(odometer_km))
                self._m365.state.odometer_km = odometer_km
                return

        elif direction == Message.Direction.ODOMETER_TO_BLE:
            if attribute == Message.Attribute.ODOMETER:
                (odometer, frame_temperature) = struct.unpack('<Ixxxxh', payload[:10])
                odometer /= 1000  # km
                frame_temperature /= 10  # C
                log.debug('Got odometer: {} km, frame_temperature: {} C'.format(odometer, frame_temperature))
                self._m365.state.odometer_km = odometer
                self._m365.state.frame_temperature = frame_temperature
                return

        log.warning('Unhandled message')
        # try:
        #     print("String: " + data[5:].decode())
        # except:
        #     pass

class M365State():
    is_connected          = False
    speed_kmh             = None
    speed_average_kmh     = None
    distance_left_km      = None    # unit?
    odometer_km           = None
    frame_temperature     = None

    battery_percent       = None
    battery_voltage       = None
    battery_capacity      = None
    battery_current       = None
    battery_temperature_1 = None
    battery_temperature_2 = None

    def as_dict(self): return self.__dict__

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class M365(Peripheral):
    RX_CHARACTERISTIC = UUID('6e400003-b5a3-f393-e0a9-e50e24dcca9e')
    TX_CHARACTERISTIC = UUID('6e400002-b5a3-f393-e0a9-e50e24dcca9e')

    def __init__(self, mac_address, delegate=None):
        Peripheral.__init__(self)
        self.mac_address = mac_address

        self.state = M365State()

        # m365 is diveded into 3 microcontrollers
        # self.bms = BatterySensor(self)
        # self.ble = EnvironmentDirection(self)
        # self.motor = MotorDirection(self)


    @staticmethod
    def _find_char(uuid: UUID, chars: Iterable[Characteristic]) -> Optional[Characteristic]:
        results = filter(lambda x: x.uuid == uuid, chars)
        for result in results:  # return the first match
            return result
        return None

    def _try_connect(self):
        log.info('Attempting to indefinitely connect to Scooter: ' + self.mac_address)
        self.state.connected = False

        while True:
            try:
                super(M365, self).connect(self.mac_address, addrType=ADDR_TYPE_RANDOM)
                log.info('Successfully connected to Scooter: ' + self.mac_address)

                # Turn on notifications, otherwise there won't be any notification
                self.writeCharacteristic(0xc, b'\x01\x00', True)
                self.writeCharacteristic(0x12, b'\x01\x00', True)

                self._all_characteristics = self.getCharacteristics()
                self._tx_char = M365._find_char(M365.TX_CHARACTERISTIC, self._all_characteristics)
                self._rx_char = M365._find_char(M365.RX_CHARACTERISTIC, self._all_characteristics)

                print('{}, handle: {:x}, properties: {}'.format(self._tx_char, self._tx_char.getHandle(), self._tx_char.propertiesToString()))
                print('{}, handle: {:x}, properties: {}'.format(self._rx_char, self._rx_char.getHandle(), self._rx_char.propertiesToString()))

                self.state.connected = True
                break

            except Exception as e:
                log.warning('{}, retrying'.format(e))

    def connect(self):
        self._try_connect()
        self.withDelegate(M365Delegate(self))

    def send(self, message):
        while True:
            try:
                log.debug('Sending data: {}'.format(phex(message)))
                self._tx_char.write(message)
                self._rx_char.read()
                break
            except Exception as e:
                log.warning('{}, reconnecting'.format(e))
                self.disconnect()
                self._try_connect()


scooter = M365('D6:0E:DB:7B:EA:AB')
scooter.connect()

# scooter.send(Message.battery_voltage)
# scooter.send(Message.battery_ampere)
# scooter.send(Message.battery_percentage)
# scooter.send(Message.speed)
# scooter.waitForNotifications(5.0)

update_interval_s = 5.0
while True:
    start_time = time.time()
    scooter.send(Message.trip_supermaster)
    scooter.send(Message.distance_supermaster)
    scooter.send(Message.battery_supermaster)
    # TODO: better check if all data was received
    received_within_timeout = scooter.waitForNotifications(update_interval_s)
    if not received_within_timeout: continue

    scooter_state = scooter.state.as_dict()
    print(scooter_state)

    elapsed_time = time.time() - start_time
    sleep_time = max(update_interval_s - elapsed_time, 0)
    time.sleep(sleep_time)


scooter.disconnect()

