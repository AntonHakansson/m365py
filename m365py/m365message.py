import binascii
import struct

def phex(s):
    return binascii.hexlify(s)

HEADER = 0xAA55

class Direction():
    MASTER_TO_MOTOR      = 0x20
    MASTER_TO_BATTERY    = 0x22
    MOTOR_TO_MASTER      = 0x23
    BATTERY_TO_MASTER    = 0x25

class ReadWrite():
    READ  = 0x01
    WRITE = 0x03

class Attribute():
    GENERAL_INFO           = 0x10 # serial, pin, fwversion
    # GENERAL_INFO_EXTENDED  = 0x10 # TODO: serial, fwversion, totalcapacity, cycles, chargingtimes, productiondate
    DISTANCE_LEFT          = 0x25
    BATTERY_INFO           = 0x31 # remaining cap, percent, current, voltage, temperature
    BATTERY_PERCENT        = 0x32
    BATTERY_CURRENT        = 0x33
    BATTERY_VOLTAGE        = 0x34
    BATTERY_CELL_VOLTAGES  = 0x40 # cell voltages (Cells 1-10)
    TRIP_INFO              = 0x3A # ontime, trip_distance_m?(seems to increment if throttle is applied), frametemp1
    SPEED                  = 0xB5
    TRIP_DISTANCE          = 0xB9
    CRUISE                 = 0x7C
    TAIL_LIGHT             = 0x7D
    MOTOR_INFO             = 0xB0 # error warning flags workmode battery_percent speed_kmh speed_average_kmh odometer_km trip_distance_m uptime_s frame_temperature
    SUPPLEMENTARY          = 0x7B # kers, cruisemode, taillight

class ParseStatus:
    OK               = 'ok'
    DISJOINTED       = 'disjointed'
    INVALID_HEADER   = 'invalid_header'
    INVALID_CHECKSUM = 'invalid_checksum'

class Message:

    def __init__(self):
        self._direction  = None
        self._read_write = None
        self._attribute  = None
        self._payload    = None

        self._checksum  = None
        self._raw_bytes  = None

    def as_dict(self): return self.__dict__

    def direction(self, direction):
        self._direction = direction
        return self

    def read_write(self, read_write):
        self._read_write = read_write
        return self

    def attribute(self, attribute) :
        self._attribute = attribute
        return self

    # For now payload is stored in little endian format
    def payload(self, payload):
        self._payload = payload
        return self

    def _calc_checksum(self):
        checksum = 0
        checksum += self._direction
        checksum += self._read_write
        checksum += self._attribute

        try:
          for byte in self._payload:
              byte_val = struct.unpack('>B', byte)[0]
              checksum += byte_val
        except:
          for byte_val in self._payload:
              checksum += byte_val

        checksum += len(self._payload) + 2
        checksum ^= 0xffff
        checksum &= 0xffff

        self._checksum = checksum


    def build(self):
        self._calc_checksum()

        result = bytearray()
        result.extend(struct.pack('<H', HEADER))
        # >>>> these are single byte so we don't have to worry about byte order
        result.append(len(self._payload) + 2)
        result.append(self._direction)
        result.append(self._read_write)
        result.append(self._attribute)
        # <<<<
        result.extend(self._payload) # TODO: store payload as big endian in class
        result.extend(struct.pack('<H', self._checksum))

        self._raw_bytes = bytes(result)
        return self

    @staticmethod
    def parse_from_bytes(message):
        message_length = len(message)
        payload_start = 6
        header, length, direction, read_write, attribute = struct.unpack('<HBBBB', message[:payload_start])
        payload_end = payload_start + length - 2

        if header != HEADER:              return ParseStatus.INVALID_HEADER , None
        if payload_end > message_length:  return ParseStatus.DISJOINTED     , None

        payload    = message[payload_start:payload_end]

        result = Message()          \
            .direction(direction)   \
            .read_write(read_write) \
            .attribute(attribute)   \
            .payload(payload)       \
            .build()

        if message[:-2] !=  result._raw_bytes[:-2]:
            return ParseStatus.INVALID_CHECKSUM, None

        return ParseStatus.OK, result

battery_voltage = Message()                       \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.BATTERY_VOLTAGE)         \
    .payload(b'\x02')                             \
    .build()

battery_ampere = Message()                        \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.BATTERY_CURRENT)         \
    .payload(b'\x02')                             \
    .build()

battery_percentage = Message()                    \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.BATTERY_PERCENT)         \
    .payload(b'\x02')                             \
    .build()

battery_cell_voltages = Message()                 \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.BATTERY_CELL_VOLTAGES)   \
    .payload(b'\x1B')                             \
    .build()

trip_distance = Message()                \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.TRIP_DISTANCE)  \
    .payload(b'\x02')                             \
    .build()

distance_left = Message()                         \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.DISTANCE_LEFT)           \
    .payload(b'\x02')                             \
    .build()

speed = Message()                                 \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.SPEED)                   \
    .payload(b'\x02')                             \
    .build()

tail_light_status = Message()                     \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.TAIL_LIGHT)              \
    .payload(b'\x02')                             \
    .build()

turn_on_tail_light = Message()                    \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.WRITE)                  \
    .attribute(Attribute.TAIL_LIGHT)              \
    .payload(b'\x02\x00')                         \
    .build()

turn_off_tail_light = Message()                   \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.WRITE)                  \
    .attribute(Attribute.TAIL_LIGHT)              \
    .payload(b'\x00\x00')                         \
    .build()

cruise_status = Message()                         \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.CRUISE)                  \
    .payload(b'\x02')                             \
    .build()

general_info = Message()                          \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.GENERAL_INFO)            \
    .payload(b'\x16')                             \
    .build()

trip_info = Message()                             \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.TRIP_INFO)               \
    .payload(b'\x0A')                             \
    .build()

motor_info = Message()                            \
    .direction(Direction.MASTER_TO_MOTOR)         \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.MOTOR_INFO)              \
    .payload(b'\x20')                             \
    .build()

battery_info = Message()                          \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.BATTERY_INFO)            \
    .payload(b'\x0A')                             \
    .build()

supplementary = Message()                         \
    .direction(Direction.MASTER_TO_BATTERY)       \
    .read_write(ReadWrite.READ)                   \
    .attribute(Attribute.SUPPLEMENTARY)           \
    .payload(b'\x06')                             \
    .build()

