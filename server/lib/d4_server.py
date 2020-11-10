#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import time
import uuid
import redis

from flask import escape

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_stream = config_loader.get_redis_conn("Redis_STREAM")
config_loader = None
###  ###

###  BEGIN - SENSOR CONNECTION ###

def get_all_connected_sensors(r_list=False):
    res = r_stream.smembers('active_connection')
    if r_list:
        if res:
            return list(res)
        else:
            return []
    else:
        return res

def get_all_connected_sensors_by_type(d4_type, d4_extended_type=None):
    # D4 extended type
    if d4_type == 254 and d4_extended_type:
        return r_stream.smembers('active_connection_extended_type:{}'.format(d4_extended_type))
    # type 1-253
    else:
        return r_stream.smembers('active_connection:{}'.format(d4_type))

def is_sensor_connected(sensor_uuid):
    return r_stream.sismember('active_connection', sensor_uuid)

### --- END - SENSOR CONNECTION --- ###
