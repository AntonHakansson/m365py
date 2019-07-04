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
    GET_LOCK               = 0xB2
    SET_LOCK               = 0x70
    UNSET_LOCK             = 0x71
    SUPPLEMENTARY          = 0x7B # kers_mode, cruisemode, taillight
    # TODO: Setting kers mode

class ParseStatus:
    OK               = 'ok'
    DISJOINTED       = 'disjointed'
    INVALID_HEADER   = 'invalid_header'
    INVALID_CHECKSUM = 'invalid_checksum'

class Message:

    def __init__(self):
        self.direction  = None
        self.read_write = None
        self.attribute  = None
        self.payload    = None

        self._checksum  = None
        self._raw_bytes  = None

    def set_direction(self, direction):
        self.direction = direction
        return self

    def set_read_write(self, read_write):
        self.read_write = read_write
        return self

    def set_attribute(self, attribute) :
        self.attribute = attribute
        return self

    # For now payload is stored in little endian format
    def set_payload(self, payload):
        self.payload = payload
        return self

    def _calc_checksum(self):
        checksum = 0
        checksum += self.direction
        checksum += self.read_write
        checksum += self.attribute

        # NOTE: python2x and python3x does not have compliant byte literals
        try:
            # python 2.7
            for byte in self.payload:
                byte_val = struct.unpack('>B', byte)[0]
                checksum += byte_val
        except:
            # python 3.x
            for byte_val in self.payload:
                checksum += byte_val

        checksum += len(self.payload) + 2
        checksum ^= 0xffff
        checksum &= 0xffff

        self._checksum = checksum

    def build(self):
        self._calc_checksum()

        result = bytearray()
        result.extend(struct.pack('<H', HEADER))
        # >>>> these are single byte so we don't have to worry about byte order
        result.append(len(self.payload) + 2)
        result.append(self.direction)
        result.append(self.read_write)
        result.append(self.attribute)
        # <<<<
        result.extend(self.payload) # TODO: store payload as big endian in class
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

        result = Message()              \
            .set_direction(direction)   \
            .set_read_write(read_write) \
            .set_attribute(attribute)   \
            .set_payload(payload)       \
            .build()

        if message[:-2] !=  result._raw_bytes[:-2]:
            return ParseStatus.INVALID_CHECKSUM, None

        return ParseStatus.OK, result

battery_voltage = Message()                          \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.BATTERY_VOLTAGE)        \
    .set_payload(b'\x02')                            \
    .build()

battery_ampere = Message()                           \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.BATTERY_CURRENT)        \
    .set_payload(b'\x02')                            \
    .build()

battery_percentage = Message()                       \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.BATTERY_PERCENT)        \
    .set_payload(b'\x02')                            \
    .build()

battery_cell_voltages = Message()                    \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.BATTERY_CELL_VOLTAGES)  \
    .set_payload(b'\x1B')                            \
    .build()

trip_distance = Message()                            \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.TRIP_DISTANCE)          \
    .set_payload(b'\x02')                            \
    .build()

distance_left = Message()                            \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.DISTANCE_LEFT)          \
    .set_payload(b'\x02')                            \
    .build()

speed = Message()                                    \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.SPEED)                  \
    .set_payload(b'\x02')                            \
    .build()

tail_light_status = Message()                        \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.TAIL_LIGHT)             \
    .set_payload(b'\x02')                            \
    .build()

turn_on_tail_light = Message()                       \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.TAIL_LIGHT)             \
    .set_payload(b'\x02\x00')                        \
    .build()

turn_off_tail_light = Message()                      \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.TAIL_LIGHT)             \
    .set_payload(b'\x00\x00')                        \
    .build()

cruise_status = Message()                            \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.CRUISE)                 \
    .set_payload(b'\x02')                            \
    .build()

turn_on_cruise = Message()                           \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.CRUISE)                 \
    .set_payload(b'\x01\x00')                        \
    .build()

turn_off_cruise = Message()                          \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.CRUISE)                 \
    .set_payload(b'\x00\x00')                        \
    .build()

turn_on_lock = Message()                             \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.SET_LOCK)               \
    .set_payload(b'\x01\x00')                        \
    .build()

turn_off_lock = Message()                            \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.WRITE)                 \
    .set_attribute(Attribute.UNSET_LOCK)             \
    .set_payload(b'\x01\x00')                        \
    .build()

lock_status = Message()                              \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.GET_LOCK)               \
    .set_payload(b'\x02')                            \
    .build()

general_info = Message()                             \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.GENERAL_INFO)           \
    .set_payload(b'\x16')                            \
    .build()

general_info_extended = Message()                    \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.GENERAL_INFO)           \
    .set_payload(b'\x22')                            \
    .build()

trip_info = Message()                                \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.TRIP_INFO)              \
    .set_payload(b'\x0A')                            \
    .build()

motor_info = Message()                               \
    .set_direction(Direction.MASTER_TO_MOTOR)        \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.MOTOR_INFO)             \
    .set_payload(b'\x20')                            \
    .build()

battery_info = Message()                             \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.BATTERY_INFO)           \
    .set_payload(b'\x0A')                            \
    .build()

supplementary = Message()                            \
    .set_direction(Direction.MASTER_TO_BATTERY)      \
    .set_read_write(ReadWrite.READ)                  \
    .set_attribute(Attribute.SUPPLEMENTARY)          \
    .set_payload(b'\x06')                            \
    .build()

