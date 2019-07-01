from typing import Callable, Iterable, Optional
from collections import namedtuple
from dataclasses import dataclass
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

class M365Message: pass

class M365MessageBuilder:
    def __init__(self):
        self._message = M365Message()
        self._checksum = 0
        self._direction = 0
        self._read_write = 0
        self._attribute = 0
        self._payload = []

    def direction(self, direction):
        self._message.direction = direction
        direction = direction.value.to_bytes(1, 'big')
        self._direction = int.from_bytes(direction, 'big', signed=True)
        self._checksum += self._direction
        return self

    def read_write(self, read_write):
        self._message.read_write = read_write
        read_write = read_write.value.to_bytes(1, 'big')
        self._read_write = int.from_bytes(read_write, 'big', signed=True)
        self._checksum += self._read_write
        return self

    def attribute(self, attribute) :
        self._message.attribute = attribute
        attribute = attribute.value.to_bytes(1, 'big')
        self._attribute = int.from_bytes(attribute, 'big', signed=True)
        self._checksum += self._attribute
        return self

    def payload(self, payload):
        self._message.payload = payload
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
        message.append(self._attribute)
        message += self._payload

        checksum = self._checksum ^ 0xffff

        message.append(int.from_bytes((checksum & 0xff).to_bytes(1, 'big'), 'big', signed=True))
        message.append(-1)
        # message.append(int.from_bytes(((checksum >> 8) & 0x000000ff).to_bytes(1, 'big', signed=False), 'big', signed=True))
        m = bytearray()
        for a in message:
            m.extend(a.to_bytes(1, 'big', signed=True))

        self._message.raw_bytes = m
        return self._message

class M365Message:
    class Direction(Enum):
        MASTER_TO_MOTOR      = 0x20
        #MOTOR_TO_MASTER      = 0x21
        MASTER_TO_BATTERY    = 0x22
        MOTOR_TO_MASTER      = 0x23
        BATTERY_TO_MASTER    = 0x25

    class ReadWrite(Enum):
        READ  = 0x01
        WRITE = 0x03

    class Attribute(Enum):
        DISTANCE_LEFT          = 0x25
        BATTERY_INFO           = 0x31
        BATTERY_PERCENTAGE     = 0x32
        BATTERY_CURRENT        = 0x33
        BATTERY_VOLTAGE        = 0x34
        SPEED                  = 0xB5
        DISTANCE_SINCE_STARTUP = 0xB9
        CRUISE                 = 0x7C
        LIGHT                  = 0x7D
        MOTOR_INFO             = 0xB0

    def __init__(self):
        self.direction  = None
        self.read_write = None
        self.attribute  = None
        self.payload    = None
        self.raw_bytes  = None

    def as_dict(self): return self.__dict__

    get_battery_voltage = M365MessageBuilder()        \
        .direction(Direction.MASTER_TO_BATTERY)       \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.BATTERY_VOLTAGE)         \
        .payload([0x02])                              \
        .build()

    get_battery_ampere = M365MessageBuilder()         \
        .direction(Direction.MASTER_TO_BATTERY)       \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.BATTERY_CURRENT)         \
        .payload([0x02])                              \
        .build()

    get_battery_percentage = M365MessageBuilder()     \
        .direction(Direction.MASTER_TO_BATTERY)       \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.BATTERY_PERCENTAGE)      \
        .payload([0x02])                              \
        .build()

    get_distance_since_startup = M365MessageBuilder() \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.DISTANCE_SINCE_STARTUP)  \
        .payload([0x02])                              \
        .build()

    get_distance_left = M365MessageBuilder()          \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.DISTANCE_LEFT)           \
        .payload([0x02])                              \
        .build()

    get_speed = M365MessageBuilder()                  \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.SPEED)                   \
        .payload([0x02])                              \
        .build()

    # >>>> NOTE: These do not affect physical light but read/writes are stored
    # >>>> in scooter memory
    get_light_status = M365MessageBuilder()           \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.LIGHT)                   \
        .payload([0x02])                              \
        .build()

    turn_on_light = M365MessageBuilder()              \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.WRITE)                  \
        .attribute(Attribute.LIGHT)                   \
        .payload([0x02, 0x00])                        \
        .build()

    turn_off_light = M365MessageBuilder()             \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.WRITE)                  \
        .attribute(Attribute.LIGHT)                   \
        .payload([0x00, 0x00])                        \
        .build()

    get_cruise_status = M365MessageBuilder()          \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.CRUISE)                  \
        .payload([0x02])                              \
        .build()
    # <<<<

    motor_info = M365MessageBuilder()                 \
        .direction(Direction.MASTER_TO_MOTOR)         \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.MOTOR_INFO)              \
        .payload([0x20])                              \
        .build()

    battery_info = M365MessageBuilder()               \
        .direction(Direction.MASTER_TO_BATTERY)       \
        .read_write(ReadWrite.READ)                   \
        .attribute(Attribute.BATTERY_INFO)            \
        .payload([0x0A])                              \
        .build()


def phex(s):
    return ''.join('/x{:02x}'.format(x) for x in s)

class M365Delegate(DefaultDelegate):
    def __init__(self, m365):
        DefaultDelegate.__init__(self)
        self._m365 = m365
        self.motor_info_first_part = None

    @staticmethod
    def zip_namedtuple_with_tuple(named_tuple, tuple_values):
        # Zip namedtuple with corresponding tuple value
        return dict(named_tuple._asdict(named_tuple._make(tuple_values)))

    def handleNotification(self, cHandle, data):
        payload = bytes(data)

        # sometimes scooter sends empty payload, ignore these
        if len(payload) == 0: return

        log.debug("Notification received from {}: {}".format(cHandle, phex(data)))
        direction, attribute = struct.unpack('<xxxBxB', payload[:6])

        try:
            direction, attribute = M365Message.Direction(direction), M365Message.Attribute(attribute)
            log.debug('{}, {}'.format(direction, attribute))
        except:
            pass

        if direction == M365Message.Direction.BATTERY_TO_MASTER:
            if attribute == M365Message.Attribute.BATTERY_INFO:
                BatteryInfo = namedtuple('BatteryInfo', 'battery_capacity battery_percent battery_current battery_voltage battery_temperature_1 battery_temperature_2')
                unpacked_tuple = struct.unpack('<HHhHBB', payload[6:16])
                result = M365Delegate.zip_namedtuple_with_tuple(BatteryInfo, unpacked_tuple)

                result['battery_capacity']      /= 1000 # Ah
                result['battery_current']       /= 100  # A
                result['battery_voltage']       /= 100  # V
                result['battery_temperature_1'] -= 20   # C
                result['battery_temperature_2'] -= 20   # C

                log.debug('Got Battery info: {}'.format(result))
                for key, value in result.items():
                    self._m365.state.__dict__[key] = value

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, result)

            elif attribute == M365Message.Attribute.BATTERY_VOLTAGE:
                (voltage,) = struct.unpack('<H', payload[6:8])
                voltage /= 100 # V
                log.debug('Got voltage: {} V'.format(voltage))
                self._m365.state.battery_voltage = voltage

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, voltage)

            elif attribute == M365Message.Attribute.BATTERY_CURRENT:
                (current,) = struct.unpack('<h', payload[6:8])
                current /= 100 # A
                log.debug('Got current: {} A'.format(current))
                self._m365.state.battery_current = current

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, current)

            elif attribute == M365Message.Attribute.BATTERY_PERCENTAGE:
                (battery_percentage,) = struct.unpack('<H', payload[6:8])
                log.debug('Got battery percentage: {} %'.format(battery_percentage))
                self._m365.state.battery_percentage = battery_percentage

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, battery_percentage)

        elif direction == M365Message.Direction.MOTOR_TO_MASTER:
            if attribute == M365Message.Attribute.MOTOR_INFO:
                # NOTE: This message is seperated into two packets, store payload and await next part
                self.motor_info_first_part = payload
                log.debug('Got motor info first part! waiting for second...')

            elif attribute == M365Message.Attribute.DISTANCE_LEFT:
                (distance_left,) = struct.unpack('<H', payload[6:8])
                distance_left /= 100
                log.debug('Got distance left: {} km'.format(distance_left))
                self._m365.state.distance_left_km = distance_left

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, distance_left)

            elif attribute == M365Message.Attribute.SPEED:
                (speed,) = struct.unpack('<H', payload[6:8])
                speed /= 100
                log.debug('Got speed: {} kmh'.format(speed))
                self._m365.state.speed_kmh = speed

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, speed)

            elif attribute == M365Message.Attribute.DISTANCE_SINCE_STARTUP:
                (distance_since_startup,) = struct.unpack('<H', payload[6:8])
                distance_since_startup_km = distance_since_startup / 1000
                log.debug('Got distance since startup: {} km'.format(distance_since_startup_km))
                self._m365.state.distance_since_startup_km = distance_since_startup_km

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, distance_since_startup_km)

            elif attribute == M365Message.Attribute.LIGHT:
                is_light_on = payload[6] == 0x02
                log.debug('Got light on: {}'.format(is_light_on))
                self._m365.state.is_light_on = is_light_on

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, is_light_on)

            elif attribute == M365Message.Attribute.CRUISE:
                is_cruise_on = payload[6] == 0x01
                log.debug('Got cruise on: {}'.format(is_cruise_on))
                self._m365.state.is_in_cruise_mode = is_cruise_on

                if self._m365._callback:
                    self._m365._callback(self._m365, direction, attribute, is_cruise_on)

        elif self.motor_info_first_part != None:
            combined_payload = bytearray()
            combined_payload.extend(self.motor_info_first_part)
            combined_payload.extend(payload)
            combined_payload = bytes(combined_payload)

            MotorInfo = namedtuple('MotorInfo', 'error warning flags workmode battery speed speed_average odometer frame_temperature')
            unpacked_tuple = struct.unpack('<HHHHHHHIxxxxhxxxxxxxx', combined_payload[6:38])

            result = M365Delegate.zip_namedtuple_with_tuple(MotorInfo, unpacked_tuple)

            result['speed']             /= 100  # km /h
            result['speed_average']     /= 100  # km /h
            result['odometer']          /= 1000 # km
            result['frame_temperature'] /= 10   # °C

            log.debug('Got Motor Info: {}'.format(result))
            self._m365.state.speed_kmh         = result['speed']
            self._m365.state.speed_average_kmh = result['speed_average']
            self._m365.state.odometer_km       = result['odometer']
            self._m365.state.frame_temperature = result['frame_temperature']

            self.motor_info_first_part = None

            if self._m365._callback:
                self._m365._callback(self._m365, direction, attribute, result)
        else:
            log.warning('Unhandled message')



@dataclass
class M365State():
    speed_kmh                 : float = None
    speed_average_kmh         : float = None
    distance_left_km          : float = None
    odometer_km               : float = None
    distance_since_startup_km : float = None
    frame_temperature         : float = None # °C
    is_light_on               : bool  = None # bool
    is_in_cruise_mode         : bool  = None

    battery_percent       : int   = None # %
    battery_voltage       : float = None # V
    battery_capacity      : float = None # Ah
    battery_current       : float = None # A
    battery_temperature_1 : float = None # °C
    battery_temperature_2 : float = None # °C

    def as_dict(self): return self.__dict__

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class M365(Peripheral):
    RX_CHARACTERISTIC = UUID('6e400003-b5a3-f393-e0a9-e50e24dcca9e')
    TX_CHARACTERISTIC = UUID('6e400002-b5a3-f393-e0a9-e50e24dcca9e')

    def __init__(self, mac_address, callback=None):
        Peripheral.__init__(self)
        self.mac_address = mac_address

        self.state = M365State()
        self._callback = callback

    @staticmethod
    def _find_characteristic(uuid: UUID, chars: Iterable[Characteristic]) -> Optional[Characteristic]:
        results = filter(lambda x: x.uuid == uuid, chars)
        for result in results:  # return the first match
            return result
        return None

    def _try_connect(self):
        log.info('Attempting to indefinitely connect to Scooter: ' + self.mac_address)

        while True:
            try:
                super(M365, self).connect(self.mac_address, addrType=ADDR_TYPE_RANDOM)
                log.info('Successfully connected to Scooter: ' + self.mac_address)

                # Turn on notifications, otherwise there won't be any notification
                self.writeCharacteristic(0xc, b'\x01\x00', True)
                self.writeCharacteristic(0x12, b'\x01\x00', True)

                self._all_characteristics = self.getCharacteristics()
                self._tx_char = M365._find_characteristic(M365.TX_CHARACTERISTIC, self._all_characteristics)
                self._rx_char = M365._find_characteristic(M365.RX_CHARACTERISTIC, self._all_characteristics)

                print('{}, handle: {:x}, properties: {}'.format(self._tx_char, self._tx_char.getHandle(), self._tx_char.propertiesToString()))
                print('{}, handle: {:x}, properties: {}'.format(self._rx_char, self._rx_char.getHandle(), self._rx_char.propertiesToString()))

                break

            except Exception as e:
                log.warning('{}, retrying'.format(e))

    def connect(self):
        self._try_connect()
        self.withDelegate(M365Delegate(self))

    def send(self, message):
        while True:
            try:
                log.debug('Sending message: {}'.format([v for (k,v) in message.__dict__.items()]))
                log.debug('Sending bytes: {}'.format(phex(message.raw_bytes)))
                self._tx_char.write(message.raw_bytes)
                self._rx_char.read()
                break
            except Exception as e:
                log.warning('{}, reconnecting'.format(e))
                self.disconnect()
                self._try_connect()

