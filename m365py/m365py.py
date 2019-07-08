from .m365message import *

from collections import namedtuple

import struct
import time
import json
import logging

from bluepy.btle import Peripheral, Characteristic, UUID, DefaultDelegate, ADDR_TYPE_RANDOM

log = logging.getLogger('m365py')

class KersMode():
    WEAK   = 0x00
    MEDIUM = 0x01
    STRONG = 0x02

class M365Delegate(DefaultDelegate):
    def __init__(self, m365):
        DefaultDelegate.__init__(self)
        self._m365 = m365
        self._disjointed_messages = []

    @staticmethod
    def unpack_to_dict(fields, unpacked_tuple):
        result = namedtuple('namedtuple', fields)
        result = result._make(unpacked_tuple) # insert unpacked values
        result = result._asdict()             # convert to OrderedDict
        result = dict(result)                 # convert to regular dict
        return result

    def handle_message(self, message):
        log.debug("Received message: {}".format(message.__dict__))
        log.debug("Payload: {}".format(phex(message.payload)))

        result = {}
        if message.attribute == Attribute.DISTANCE_LEFT:
            result = M365Delegate.unpack_to_dict(
                'distance_left_km',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.SPEED:
            result = M365Delegate.unpack_to_dict(
                'speed_kmh',
                struct.unpack('<h', message.payload)
            )

        elif message.attribute == Attribute.TRIP_DISTANCE:
            result = M365Delegate.unpack_to_dict(
                'trip_distance_m',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.TAIL_LIGHT:
            result = M365Delegate.unpack_to_dict(
                'is_tail_light_on',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.CRUISE:
            result = M365Delegate.unpack_to_dict(
                'is_cruise_on',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.GET_LOCK:
            result = M365Delegate.unpack_to_dict(
                'is_lock_on',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.BATTERY_INFO:
            result = M365Delegate.unpack_to_dict(
                'battery_capacity battery_percent battery_current battery_voltage battery_temperature_1 battery_temperature_2',
                struct.unpack('<HHhHBB', message.payload)
            )

        elif message.attribute == Attribute.BATTERY_VOLTAGE:
            result = M365Delegate.unpack_to_dict(
                'battery_voltage',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.BATTERY_CURRENT:
            result = M365Delegate.unpack_to_dict(
                'battery_current',
                struct.unpack('<h', message.payload)
            )

        elif message.attribute == Attribute.BATTERY_PERCENT:
            result = M365Delegate.unpack_to_dict(
                'battery_percent',
                struct.unpack('<H', message.payload)
            )

        elif message.attribute == Attribute.GENERAL_INFO:
            #          [                      SERIAL                          ][          PIN         ][ VER  ]
            # payload: /x31/x36/x31/x33/x32/x2f/x30/x30/x30/x39/x35/x32/x39/x32/x30/x30/x30/x30/x30/x30/x38/x01
            result = M365Delegate.unpack_to_dict(
                'serial pin version',
                struct.unpack('<14s6sH', message.payload)
            )

        elif message.attribute == Attribute.MOTOR_INFO:
            result = M365Delegate.unpack_to_dict(
                # 'error warning flags workmode battery_percent speed_kmh speed_average_kmh odometer_km trip_distance_m uptime_s frame_temperature',
                'battery_percent speed_kmh speed_average_kmh odometer_km trip_distance_m uptime_s frame_temperature',
                struct.unpack('<xxxxxxxxHhHIhhhxxxxxxxx', message.payload)
            )

        elif message.attribute == Attribute.TRIP_INFO:
            #          [uptime][]
            # payload: xec/x00 /x00/x00/x00/x00/x00/x00/xe6/x00
            result = M365Delegate.unpack_to_dict(
                'uptime_s trip_distance_m frame_temperature',
                struct.unpack('<HIxxh', message.payload)
            )

        elif message.attribute == Attribute.BATTERY_CELL_VOLTAGES:
            #          [cell1 ][cell2 ]                     ...                                [cell10][           ???            ]
            # payload: /x2d/x10/x2e/x10/x1d/x10/x2f/x10/x34/x10/x34/x10/x3a/x10/x3a/x10/x2e/x10/x2f/x10/x00/x00/x00/x00/x00/x00/x00
            cell_voltages_tuple = struct.unpack('<HHHHHHHHHHxxxxxxx', message.payload)

            result['cell_voltages'] = []

            for voltage in cell_voltages_tuple:
                result['cell_voltages'].append(float(voltage) / 100) # V

        elif message.attribute == Attribute.SUPPLEMENTARY:
            # TODO:  Proper states for kers mode instead of byte value
            #          [ kers ] [cruise] [taillight]
            # payload: /x00/x00 /x00/x00 /x00/x00
            result = M365Delegate.unpack_to_dict(
                'kers_mode is_cruise_on is_tail_light_on',
                struct.unpack('<HHH', message.payload)
            )

        else:
            log.warning('Unhandled message!')
            return

        def try_update_field(result, key, func):
            if key in result:
                new_val = func(result[key])
                result[key] = new_val

        # Convert raw bytes to corresponing type
        try_update_field(result, 'serial',                lambda x: x.decode('utf-8')) # str
        try_update_field(result, 'pin',                   lambda x: x.decode('utf-8')) # str
        try_update_field(result, 'speed_kmh',             lambda x: float(x) / 100)  # km/h
        try_update_field(result, 'speed_average_kmh',     lambda x: float(x) / 100)  # km/h
        try_update_field(result, 'distance_left_km',      lambda x: float(x) / 100)  # km
        try_update_field(result, 'frame_temperature',     lambda x: float(x) / 10)   # C
        try_update_field(result, 'odometer_km',           lambda x: float(x) / 1000) # km
        try_update_field(result, 'battery_capacity',      lambda x: float(x) / 1000) # Ah
        try_update_field(result, 'battery_current',       lambda x: float(x) / 100)  # A
        try_update_field(result, 'battery_voltage',       lambda x: float(x) / 100)  # V
        try_update_field(result, 'battery_temperature_1', lambda x: x - 20)   # C
        try_update_field(result, 'battery_temperature_2', lambda x: x - 20)   # C
        try_update_field(result, 'is_tail_light_on',      lambda x: x == 0x02)   # bool
        try_update_field(result, 'is_lock_on',            lambda x: x == 0x02)   # bool
        try_update_field(result, 'is_cruise_on',          lambda x: x == 0x01)   # bool

        if 'version' in result:
            result['version'] = '{:02x}'.format(result['version'])
            result['version'] = 'V' + '.'.join(result['version'])  # V1.3.8

        # write result to m365 cached state
        for key, value in result.items():
            # hacky way of writing key and value to state
            self._m365.cached_state[key] = value

        # call user callback
        if self._m365._callback:
            self._m365._callback(self._m365, message, result)


    def handleNotification(self, cHandle, data):
        data = bytes(data)
        log.debug('Got raw bytes: {}'.format(phex(data)))

        # sometimes we receive empty payload, ignore these
        if len(data) == 0: return
        parse_status, message = Message.parse_from_bytes(data)

        if parse_status == ParseStatus.OK:
            self.handle_message(message)

        elif parse_status == ParseStatus.DISJOINTED:
            self._disjointed_messages.append(data)

        elif parse_status == ParseStatus.INVALID_HEADER:
            # This could mean we got rest of disjointed message
            # TODO: if no matching message was found... warn the user
            for i, prev_data in enumerate(self._disjointed_messages):
                combined_data = bytearray()
                combined_data.extend(prev_data)
                combined_data.extend(data)
                combined_data = bytes(combined_data)

                # try parse combined data
                parse_status, message = Message.parse_from_bytes(combined_data)
                if parse_status == ParseStatus.OK:
                    self.handle_message(message)
                    del self._disjointed_messages[i]

        elif parse_status == ParseStatus.INVALID_CHECKSUM:
            log.warning('Received packet with invalid checksum')


class M365(Peripheral):
    RX_CHARACTERISTIC = UUID('6e400003-b5a3-f393-e0a9-e50e24dcca9e')
    TX_CHARACTERISTIC = UUID('6e400002-b5a3-f393-e0a9-e50e24dcca9e')

    def __init__(self, mac_address, callback=None, auto_reconnect=True):
        Peripheral.__init__(self)
        self.mac_address = mac_address
        self._auto_reconnect = auto_reconnect

        self.cached_state = {}
        self._callback = callback
        self._disconnected_callback = None
        self._connected_callback = None

        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)

        log.addHandler(stream_handler)

    def set_connected_callback(self, cb):
        self._connected_callback = cb

    def set_disconnected_callback(self, cb):
        self._disconnected_callback = cb

    @staticmethod
    def _find_characteristic(uuid, chars):
        results = filter(lambda x: x.uuid == uuid, chars)
        for result in results:  # return the first match
            return result
        return None

    def _try_connect(self):
        log.info('Attempting to {}connect to Scooter: {}'.format('indefinitely ' if self._auto_reconnect else '',
                                                                  self.mac_address))

        while True:
            try:
                Peripheral.connect(self, self.mac_address, addrType=ADDR_TYPE_RANDOM)
                log.info('Successfully connected to Scooter: ' + self.mac_address)
                if self._connected_callback:
                    self._connected_callback(self)

                # Attach delegate
                self.withDelegate(M365Delegate(self))

                # Turn on notifications, otherwise there won't be any notification
                self.writeCharacteristic(0xc,  b'\x01\x00', True)
                self.writeCharacteristic(0x12, b'\x01\x00', True)

                self._all_characteristics = self.getCharacteristics()
                self._tx_char = M365._find_characteristic(M365.TX_CHARACTERISTIC, self._all_characteristics)
                self._rx_char = M365._find_characteristic(M365.RX_CHARACTERISTIC, self._all_characteristics)
                break

            except Exception as e:
                if self._auto_reconnect == True:
                    log.warning('{}, retrying'.format(e))
                else:
                    raise e

    def _try_reconnect(self):
        try:
            self.disconnect()
        except:
            pass
        if self._disconnected_callback:
            self._disconnected_callback(self)
        self._try_connect()

    def connect(self):
        self._try_connect()

    def request(self, message):
        while True:
            try:
                log.debug('Sending message: {}'.format([v for (k,v) in message.__dict__.items()]))
                log.debug('Sending bytes: {}'.format(phex(message._raw_bytes)))
                self._tx_char.write(message._raw_bytes)
                self._rx_char.read()
                break
            except Exception as e:
                if self._auto_reconnect == True:
                    log.warning('{}, reconnecting'.format(e))
                    self._try_reconnect()
                else:
                    raise e

    def waitForNotifications(self, timeout):
        try:
            Peripheral.waitForNotifications(self, timeout)
        except Exception as e:
            if self._auto_reconnect == True:
                log.warning('{}, reconnecting'.format(e))
                self._try_reconnect()
            else:
                raise e

