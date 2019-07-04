from bluepy.btle import Scanner

""" Scans for available devices. """
scan = Scanner()
sec = 5
print("Scanning for %s seconds" % sec)
devs = scan.scan(sec)
print("Scooters found:")
for dev in devs:
    localname = dev.getValueText(9)
    if localname and localname.startswith("MIScooter"):
        print("  %s, addr=%s, rssi=%d" % (localname, dev.addr, dev.rssi))
