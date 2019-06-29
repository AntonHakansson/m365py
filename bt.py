import sys
import binascii
from bluepy import btle


def phex(s):
    return ''.join('{:02x}'.format(x) for x in s)

Commands = {
    "GetSerial": b'\x10\x0e',
    "GetFirmware": b'\x1a\x02',
    "GetPincode": b'\x17\x06',
}

Direction = {
    "M2S":b'\x20',
    "S2M":b'\x23',
    "M2B":b'\x22',
    "B2M":b'\x25',
}

class ScooterMessage:

    HEADER = b'\x55\xAA'

    def __init__(self, cmdname, dirname):
        self.construct(cmdname, dirname)
        
    def construct(self, cmdname, dirname):
        data = bytearray()
        data.extend(ScooterMessage.HEADER)
        print('sofar: ' + phex(data))
        data.extend(b'\xff') # pos 3: length placeholder
        data.extend(Direction[dirname]) # pos 4: Direction byte (0x20 M2S, 0x23 S2M, 0x22 M2B, 0x25 B2M)
        data.extend(b'\x01' if cmdname.startswith('Get') else b'\x03') # pos 5: Read (0x01) / Write (0x03)
        data.extend(Commands[cmdname]) # pos 6+7: Command + Param
        #data.extend(b'\xff') # pos 7: Param
        data[2] = len(data)-4
        
        # Compute & add checksum
        sum=0
        for x in data[2:]:
            sum=sum+x
        sum = sum ^ 0xffff
        data.append(sum & 0xff)
        data.append(sum >> 8 & 0xff)
      
        print("checksum: " + hex(sum))
        print("Data: " +phex(data))
      
        self.data = data

class CommManager:

    TXhandle = 0xe
    RXhandle = 0xb

    def __init__(self, macAddress):
        self.mac = macAddress
        self.dev = btle.Peripheral()

    def connect(self):
        print("Connecting...")
        self.dev.connect(self.mac, 'random')
        print("Connected!")
        
        self.dev.withDelegate( MyDelegate() )

        # Turn on notifications, otherwise there won't be any notification (took me a couple of days to figure that one out)
        self.dev.writeCharacteristic(0xc, b'\x01\x00', True)
        self.dev.writeCharacteristic(0x12, b'\x01\x00', True)

    def send(self, cmdname, dirname='M2S'):
        msg=ScooterMessage(cmdname, dirname)
        self.dev.writeCharacteristic(CommManager.TXhandle, msg.data)

        # Poke to get Response
        self.dev.readCharacteristic(CommManager.RXhandle)
        self.dev.waitForNotifications(1.0)
        self.dev.waitForNotifications(1.0)


class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        print("MyDelegate ctor")
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        print("A notification was received from %s: %s" % (str(cHandle), phex(data)))
        try:
            print("String: " + data[5:].decode())
        except:
            pass


myMAC='D6:0E:DB:7B:EA:AB'
com=CommManager(myMAC)
com.connect()
com.send('GetSerial')
com.send('GetFirmware')
com.send('GetPincode')

