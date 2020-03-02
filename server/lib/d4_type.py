#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import datetime
import time
import uuid
import redis

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_metadata = config_loader.get_redis_conn("Redis_METADATA")
config_loader = None
###  ###

def get_all_accepted_format_type(r_list=False):
    res = r_serv_metadata.smembers('server:accepted_type')
    if r_list:
        if res:
            return list(res)
        else:
            return []
    return res

def get_all_accepted_extended_type(r_list=False):
    res = r_serv_metadata.smembers('server:accepted_extended_type')
    if r_list:
        if res:
            return list(res)
        else:
            return []
    return res

def is_accepted_format_type(format_type):
    return r_serv_metadata.sismember('server:accepted_type', format_type)

def is_accepted_extended_type(extended_type):
    return r_serv_metadata.sismember('server:accepted_extended_type', extended_type)
