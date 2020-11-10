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
import d4_server

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_db = config_loader.get_redis_conn("Redis_METADATA")
config_loader = None
###  ###

def is_valid_uuid_v4(UUID):
    UUID = UUID.replace('-', '')
    try:
        uuid_test = uuid.UUID(hex=UUID, version=4)
        return uuid_test.hex == UUID
    except:
        return False

def get_time_sensor_last_seen(sensor_uuid):
    res = r_serv_db.hget('metadata_uuid:{}'.format(sensor_uuid), 'last_seen')
    if res:
        return int(res)
    else:
        return 0

def _get_sensor_type(sensor_uuid, first_seen=True, last_seen=True, time_format='default'):
    uuid_type = []
    uuid_all_type = r_serv_db.smembers('all_types_by_uuid:{}'.format(sensor_uuid))
    for type in uuid_all_type:
        type_meta = {}
        type_meta['type'] = type
        if first_seen:
            type_meta['first_seen'] = r_serv_db.hget('metadata_type_by_uuid:{}:{}'.format(sensor_uuid, type), 'first_seen')
        if last_seen:
            type_meta['last_seen'] = r_serv_db.hget('metadata_type_by_uuid:{}:{}'.format(sensor_uuid, type), 'last_seen')
        # time format
        if time_format=='gmt':
            if type_meta['first_seen']:
                type_meta['first_seen'] = datetime.datetime.fromtimestamp(float(type_meta['first_seen'])).strftime('%Y-%m-%d %H:%M:%S')
            if type_meta['last_seen']:
                type_meta['last_seen'] = datetime.datetime.fromtimestamp(float(type_meta['last_seen'])).strftime('%Y-%m-%d %H:%M:%S')
        uuid_type.append(type_meta)
    return uuid_type

def _get_sensor_metadata(sensor_uuid, first_seen=True, last_seen=True, time_format='default', sensor_types=False, mail=True, description=True):

    meta_sensor = {}
    meta_sensor['uuid'] = sensor_uuid
    if first_seen:
        meta_sensor['first_seen'] = r_serv_db.hget('metadata_uuid:{}'.format(sensor_uuid), 'first_seen')
    if last_seen:
        meta_sensor['last_seen'] = r_serv_db.hget('metadata_uuid:{}'.format(sensor_uuid), 'last_seen')
    # time format
    if time_format=='gmt':
        if meta_sensor['first_seen']:
            meta_sensor['first_seen'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(meta_sensor['first_seen'])))
        if meta_sensor['last_seen']:
            meta_sensor['last_seen'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(meta_sensor['last_seen'])))

    if sensor_types:
        meta_sensor['types'] = _get_sensor_type(sensor_uuid, first_seen=False, last_seen=False)
    if description:
        meta_sensor['description'] = r_serv_db.hget('metadata_uuid:{}'.format(sensor_uuid), 'description')
    if mail:
        meta_sensor['mail'] = r_serv_db.hget('metadata_uuid:{}'.format(sensor_uuid), 'user_mail')
    return meta_sensor

### BEGIN - SENSOR REGISTRATION ###

## TODO: add description
def register_sensor(req_dict):
    sensor_uuid = req_dict.get('uuid', None)
    hmac_key = req_dict.get('hmac_key', None)
    user_id = req_dict.get('mail', None)
    third_party = req_dict.get('third_party', None)
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
        if len(hmac_key)>100:
            hmac_key=hmac_key[:100]
    if third_party:
        third_party = True

    res = _register_sensor(sensor_uuid, hmac_key, user_id=user_id, third_party=third_party, description=None)
    return res


def _register_sensor(sensor_uuid, secret_key, user_id=None, third_party=False, description=None):
    r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'hmac_key', secret_key)
    if user_id:
        r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'user_mail', user_id)
    if description:
        r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'description', description)
    if third_party:
        r_serv_db.hset('metadata_uuid:{}'.format(sensor_uuid), 'third_party', True)
    r_serv_db.sadd('sensor_pending_registration', sensor_uuid)
    return ({'uuid': sensor_uuid}, 200)

def get_pending_sensor():
    return list(r_serv_db.smembers('sensor_pending_registration'))

def get_nb_pending_sensor():
    return r_serv_db.scard('sensor_pending_registration')

def get_nb_registered_sensors():
    return r_serv_db.scard('registered_uuid')

def get_registered_sensors():
    return list(r_serv_db.smembers('registered_uuid'))

def approve_sensor(req_dict):
    sensor_uuid = req_dict.get('uuid', None)
    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')
    # sensor not registred
    #if r_serv_db.sismember('sensor_pending_registration', sensor_uuid):
    #    return ({"status": "error", "reason": "Sensor not registred"}, 404)
    # sensor already approved
    if r_serv_db.sismember('registered_uuid', sensor_uuid):
        return ({"status": "error", "reason": "Sensor already approved"}, 409)
    return _approve_sensor(sensor_uuid)

def _approve_sensor(sensor_uuid):
    r_serv_db.sadd('registered_uuid', sensor_uuid)
    r_serv_db.srem('sensor_pending_registration', sensor_uuid)
    return ({'uuid': sensor_uuid}, 200)

def delete_pending_sensor(req_dict):
    sensor_uuid = req_dict.get('uuid', None)
    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')
    # sensor not registred
    #if r_serv_db.sismember('sensor_pending_registration', sensor_uuid):
    #    return ({"status": "error", "reason": "Sensor not registred"}, 404)
    # sensor already approved
    if not r_serv_db.sismember('sensor_pending_registration', sensor_uuid):
        return ({"status": "error", "reason": "Not Pending Sensor"}, 409)
    return _delete_pending_sensor(sensor_uuid)

def _delete_pending_sensor(sensor_uuid):
    r_serv_db.srem('sensor_pending_registration', sensor_uuid)
    return ({'uuid': sensor_uuid}, 200)

def delete_registered_sensor(req_dict):
    sensor_uuid = req_dict.get('uuid', None)
    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')
    # sensor not registred
    if not r_serv_db.sismember('registered_uuid', sensor_uuid):
        return ({"status": "error", "reason": "Sensor not registered"}, 404)
    return _delete_registered_sensor(sensor_uuid)

def _delete_registered_sensor(sensor_uuid):
    r_serv_db.srem('registered_uuid', sensor_uuid)
    return ({'uuid': sensor_uuid}, 200)

### --- END - SENSOR REGISTRATION --- ###


###  BEGIN - SENSOR MONITORING  ###
def get_sensors_monitoring_last_updated():
    res = r_serv_db.get('sensors_monitoring:last_updated')
    if res:
        return int(res)
    else:
        return 0

def get_all_sensors_to_monitor():
    return r_serv_db.smembers('to_monitor:sensors')

def get_to_monitor_delta_time_by_uuid(sensor_uuid):
    return int(r_serv_db.hget('to_monitor:sensor:{}'.format(sensor_uuid), 'delta_time'))

def get_all_sensors_to_monitor_dict():
    dict_to_monitor = {}
    for sensor_uuid in get_all_sensors_to_monitor():
        dict_to_monitor[sensor_uuid] = get_to_monitor_delta_time_by_uuid(sensor_uuid)
    return dict_to_monitor

def _check_sensor_delta(sensor_uuid, sensor_delta):
    last_d4_packet = get_time_sensor_last_seen(sensor_uuid)

    # check sensor delta time between two D4 packets + check sensor connection
    if int(time.time()) - last_d4_packet > sensor_delta or not d4_server.is_sensor_connected(sensor_uuid):
        r_serv_db.sadd('sensors_monitoring:sensors_error', sensor_uuid)
        handle_sensor_monitoring_error(sensor_uuid)
    else:
        r_serv_db.srem('sensors_monitoring:sensors_error', sensor_uuid)

def handle_sensor_monitoring_error(sensor_uuid):
    print('sensor monitoring error: {}'.format(sensor_uuid))
    ## TODO: ##
    # MAILS
    # UI Notifications
    # SNMP
    # Syslog message
    ## ## ## ##
    return None

def is_sensor_monitored(sensor_uuid):
    return r_serv_db.exists('to_monitor:sensors', sensor_uuid)

def get_all_sensors_connection_errors():
    return r_serv_db.smembers('sensors_monitoring:sensors_error')

def api_get_all_sensors_connection_errors():
    return list(get_all_sensors_connection_errors()), 200

def add_sensor_to_monitor(sensor_uuid, delta_time):
    r_serv_db.sadd('to_monitor:sensors', sensor_uuid)
    r_serv_db.hset('to_monitor:sensor:{}'.format(sensor_uuid), 'delta_time', delta_time)
    r_serv_db.set('sensors_monitoring:last_updated', int(time.time()))

def delete_sensor_to_monitor(sensor_uuid):
    r_serv_db.srem('to_monitor:sensors', sensor_uuid)
    r_serv_db.delete('to_monitor:sensor:{}'.format(sensor_uuid))
    r_serv_db.set('sensors_monitoring:last_updated', int(time.time()))
    r_serv_db.srem('sensors_monitoring:sensors_error', sensor_uuid)

def api_add_sensor_to_monitor(data_dict):
    sensor_uuid = data_dict.get('uuid', None)
    delta_time = data_dict.get('delta_time', None)

    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')

    # hmac key
    if not delta_time:
        return ({"status": "error", "reason": "Mandatory parameter(s) not provided"}, 400)
    else:
        try:
            delta_time = int(delta_time)
            if delta_time < 1:
                return ({"status": "error", "reason": "Invalid delta_time"}, 400)
        except Exception:
            return ({"status": "error", "reason": "Invalid delta_time"}, 400)
    add_sensor_to_monitor(sensor_uuid, delta_time)

def api_delete_sensor_to_monitor(data_dict):
    sensor_uuid = data_dict.get('uuid', None)
    if not is_valid_uuid_v4(sensor_uuid):
        return ({"status": "error", "reason": "Invalid uuid"}, 400)
    sensor_uuid = sensor_uuid.replace('-', '')
    if not is_sensor_monitored(sensor_uuid):
        return ({"status": "error", "reason": "Sensor not monitored"}, 400)
    delete_sensor_to_monitor(sensor_uuid)


### --- END - SENSOR REGISTRATION --- ###
