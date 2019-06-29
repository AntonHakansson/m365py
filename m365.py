from bluepy.btle import Peripheral, DefaultDelegate, UUID, ADDR_TYPE_RANDOM
import time

class MessageBuilder:
    def __init__(self):
        self._checksum = 0
        self._direction = 0
        self._read_write = 0
        self._position = 0
        self._payload = []

    def direction(self, direction):
        direction = direction.to_bytes(1, 'big')
        self._direction = int.from_bytes(direction, 'big', signed=True)
        self._checksum += self._direction
        return self

    def read_write(self, read_write):
        read_write = read_write.to_bytes(1, 'big')
        self._read_write = int.from_bytes(read_write, 'big', signed=True)
        self._checksum += self._read_write
        return self

    def position(self, position) :
        position = position.to_bytes(1, 'big')
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
        m = []
        for a in message:
            m.append(a.to_bytes(1, 'big', signed=True))

        return m

class Message:

    class Service:
        M365 = 0x20
        BATTERY = 0x22

    class Action:
        READ = 0x01
        WRITE = 0x03

    class Attribute:
        BATTERY_LIFE = 0x32
        BATTERY_AMPERE = 0x33
        BATTERY_VOLTAGE = 0x34
        DISTANCE = 0xB9
        SPEED = 0xB5
        SUPERMASTER = 0xB0

    PAYLOAD = [0x02]

    battery_voltage = MessageBuilder() \
        .direction(Service.BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_VOLTAGE) \
        .read_write(Action.READ).build()
#    battery_voltage = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'4', b'\x02', b'\xa3', b'\xff']

    battery_ampere = MessageBuilder() \
        .direction(Service.BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_AMPERE) \
        .read_write(Action.READ).build()

#    battery_ampere = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'3', b'\x02', b'\xa4', b'\xff']

    battery_life = MessageBuilder() \
        .direction(Service.BATTERY) \
        .payload(PAYLOAD) \
        .position(Attribute.BATTERY_LIFE) \
        .read_write(Action.READ).build()

#    battery_life = [b'U', b'\xaa', b'\x03', b'"', b'\x01', b'2', b'\x02', b'\xa5', b'\xff']]
    distance = MessageBuilder() \
        .direction(Service.M365) \
        .payload(PAYLOAD) \
        .position(Attribute.DISTANCE) \
        .read_write(Action.READ).build()

    speed = MessageBuilder() \
        .direction(Service.M365) \
        .payload(PAYLOAD) \
        .position(Attribute.SPEED) \
        .read_write(Action.READ).build()

    supermaster = MessageBuilder() \
        .direction(Service.M365) \
        .payload(PAYLOAD) \
        .position(Attribute.SUPERMASTER) \
        .read_write(Action.READ).build()


class M365Delegate(DefaultDelegate):
    def __init__(self, m365):
        self.m365 = m365

    def handleNotification(self, hnd, data):
        print('received notification {} {}'.format(hnd, data))


class M365(Peripheral):
    MAIN_SERVICE_UUID = UUID('6e400001-b5a3-f393-e0a9-e50e24dcca9e')
    TX_CHARACTERISTIC = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
    RX_CHARACTERISTIC = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'

    def __init__(self, mac_address, delegate=None):
        Peripheral.__init__(self)

        self.mac_address = mac_address
        self.withDelegate(M365Delegate(self))

        # m365 is diveded into 3 microcontrollers
        # self.bms = BatterySensor(self)
        # self.ble = EnvironmentService(self)
        # self.motor = MotorService(self)


    def connect(self):
        print('connecting ...')
        super(M365, self).connect(self.mac_address, addrType=ADDR_TYPE_RANDOM)
        print('connected!')

        # Turn on notifications, otherwise there won't be any notification (took me a couple of days to figure that one out)
        self.writeCharacteristic(0xc, b'\x01\x00', True)
        self.writeCharacteristic(0x12, b'\x01\x00', True)

        self.m365_service = self.getServiceByUUID(M365.MAIN_SERVICE_UUID)

        time.sleep(5)
        print('characteristics ...')
        for ch in self.getCharacteristics():
            print('characteristic: {}, uuid: {}, handle: {:x}'.format(ch, ch.uuid, ch.getHandle()))



scooter = M365('D6:0E:DB:7B:EA:AB')
scooter.connect()

time.sleep(10)
