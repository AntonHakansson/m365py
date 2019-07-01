from m365py import *

scooter_mac_address = 'D6:0E:DB:7B:EA:AB'

scooter = M365(scooter_mac_address)
scooter.connect()

update_interval_s = 5.0
while True:
    start_time = time.time()
    scooter.send(M365Message.trip_supermaster)
    scooter.send(M365Message.get_distance_left)
    scooter.send(M365Message.battery_info)

    # TODO: better check if all data was received
    received_within_timeout = scooter.waitForNotifications(update_interval_s)
    if not received_within_timeout: continue

    scooter_state = scooter.state.to_json()
    print(scooter_state)

    elapsed_time = time.time() - start_time
    sleep_time = max(update_interval_s - elapsed_time, 0)
    time.sleep(sleep_time)

scooter.disconnect()
