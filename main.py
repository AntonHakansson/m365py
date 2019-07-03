import logging

from m365py import *

def callback(m365_peripheral, message, value):
    print('End user got {}'.format(value))

scooter_mac_address = 'D6:0E:DB:7B:EA:AB'
scooter = M365(scooter_mac_address, callback)
scooter.connect()

update_interval_s = 5.0

scooter.request(M365Message.turn_off_tail_light)
while True:
    start_time = time.time()
    # scooter.request(M365Message.battery_cell_voltages)
    # scooter.request(M365Message.trip_info)
    # scooter.request(M365Message.supplementary)
    # scooter.request(M365Message.motor_info)
    scooter.request(M365Message.general_info)
    # scooter.request(M365Message.distance_left)
    # scooter.request(M365Message.battery_info)

    received_within_timeout = scooter.waitForNotifications(update_interval_s)
    received_within_timeout = scooter.waitForNotifications(update_interval_s)
    if not received_within_timeout: continue

    # scooter_state = scooter.state.to_json()
    # print(scooter_state)

    elapsed_time = time.time() - start_time
    sleep_time = max(update_interval_s - elapsed_time, 0)
    time.sleep(sleep_time)

scooter.disconnect()

