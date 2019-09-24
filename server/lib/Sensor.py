#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import uuid
import redis

from Flask import escape

host_redis_metadata = os.getenv('D4_REDIS_METADATA_HOST', "localhost")
port_redis_metadata = int(os.getenv('D4_REDIS_METADATA_PORT', 6380))

r_serv_db = redis.StrictRedis(
    host=host_redis_metadata,
    port=port_redis_metadata,
    db=0)

def is_valid_uuid_v4(UUID):
    UUID = UUID.replace('-', '')
    try:
        uuid_test = uuid.UUID(hex=UUID, version=4)
        return uuid_test.hex == UUID
    except:
        return False

## TODO: add description
def register_sensor(req_dict):
    sensor_uuid = req_dict.get('uuid', None)
    hmac_key = req_dict.get('hmac_key', None)
    user_id = req_dict.get('mail', None)
    # verify uuid
    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')
    # sensor already exist
    if r_serv_db.exists('metadata_uuid:{}'.format(sensor_uuid)):
        return ({"status": "error", "reason": "Sensor already registred"}, 409)

    # hmac key
    if not hmac_key:
        return ({"status": "error", "reason": "Mandatory parameter(s) not provided"}, 400)
    else:
        hmac_key = escape(hmac_key)


    res = _register_sensor(sensor_uuid, hmac_key, user_id=user_id, description=None)
    return res


def _register_sensor(sensor_uuid, secret_key, user_id=None, description=None):
    r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'hmac_key', secret_key)
    if user_id:
        r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'user_mail', user_id)
    if description:
        r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'description', description)
    return ({'uuid': sensor_uuid}, 200)
