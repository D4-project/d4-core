#!/usr/bin/env python3

import os
import sys
import time
import redis

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader
import Sensor

### Config ###
config_loader = ConfigLoader.ConfigLoader()
#redis_server_stream = config_loader.get_redis_conn("Redis_STREAM", decode_responses=False)
redis_server_metadata = config_loader.get_redis_conn("Redis_METADATA")
config_loader = None
###  ###

try:
    redis_server_metadata.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server: Redis_METADATA, ConnectionError')
    sys.exit(1)


def reload_all_sensors_to_monitor_dict(dict_to_monitor, last_updated):
    if not dict_to_monitor:
        dict_to_monitor = Sensor.get_all_sensors_to_monitor_dict()
    else:
        monitoring_last_updated = Sensor.get_sensors_monitoring_last_updated()
        if monitoring_last_updated > last_updated:
            dict_to_monitor = Sensor.get_all_sensors_to_monitor_dict()
            last_updated = int(time.time())
            print('updated: List of sensors to monitor')

if __name__ == "__main__":

    time_refresh = int(time.time())
    last_updated = time_refresh
    all_sensors_to_monitor = Sensor.get_all_sensors_to_monitor_dict()

    while True:

        for sensor_uuid in all_sensors_to_monitor:
            Sensor._check_sensor_delta(sensor_uuid, all_sensors_to_monitor[sensor_uuid])
        time.sleep(10)

        ## reload dict_to_monitor ##
        curr_time = int(time.time())
        if curr_time - time_refresh >= 60:
            time_refresh = curr_time
            reload_all_sensors_to_monitor_dict(all_sensors_to_monitor, last_updated)
        ##--  --##
