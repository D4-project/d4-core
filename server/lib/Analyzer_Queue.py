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
r_serv_analyzer = config_loader.get_redis_conn("Redis_ANALYZER")
LIST_DEFAULT_SIZE = config_loader.get_config_int('D4_Server', 'analyzer_queues_max_size')
config_loader = None
###  ###

def is_valid_uuid_v4(uuid_v4):
    if uuid_v4:
        uuid_v4 = uuid_v4.replace('-', '')
    else:
        return False

    try:
        uuid_test = uuid.UUID(hex=uuid_v4, version=4)
        return uuid_test.hex == uuid_v4
    except:
        return False

def sanitize_uuid(uuid_v4):
    if not is_valid_uuid_v4(uuid_v4):
        uuid_v4 = str(uuid.uuid4())
    return uuid_v4

def get_all_queues(r_list=None):
    res = r_serv_metadata.smembers('all_analyzer_queues')
    if r_list:
        return list(res)
    return res

def get_all_queues_standard_format(r_list=None):
    res = r_serv_metadata.smembers('all_analyzer_queues')
    if r_list:
        return list(res)
    return res

def get_all_queues_standard_extended_format(r_list=None):
    res = r_serv_metadata.smembers('all_analyzer_queues')
    if r_list:
        return list(res)
    return res

def get_all_queues_by_type(format_type, r_list=None):
    '''
    Get all analyzer Queues by type

    :param format_type: data type
    :type domain_type: int
    :param r_list: return list
    :type r_list: boolean

    :return: list or set of queus (uuid)
    :rtype: list or set
    '''
    # 'all_analyzer_queues_by_type'
    res = r_serv_metadata.smembers('analyzer:{}'.format(format_type))
    if r_list:
        return list(res)
    return res

def get_all_queues_group_by_type(format_type, r_list=None):
    res = r_serv_metadata.smembers('analyzer_uuid_group:{}'.format(format_type))
    if r_list:
        return list(res)
    return res

def get_all_queues_by_sensor_group(format_type, sensor_uuid, r_list=None):
    print('sensor:queues:{}:{}'.format(format_type, sensor_uuid))
    res = r_serv_metadata.smembers('sensor:queues:{}:{}'.format(format_type, sensor_uuid))
    if r_list:
        return list(res)
    return res

def get_queue_group_all_sensors(queue_uuid, r_list=None):
    res = r_serv_metadata.smembers('analyzer_sensor_group:{}'.format(queue_uuid))
    if r_list:
        return list(res)
    return res

def get_queue_last_seen(queue_uuid, f_date='str_time'):
    res = r_serv_metadata.hget('analyzer:{}'.format(queue_uuid), 'last_updated')
    if f_date == 'str_date':
        if res is None:
            res = 'Never'
        else:
            res = datetime.datetime.fromtimestamp(float(res)).strftime('%Y-%m-%d %H:%M:%S')
    return res

def get_queue_max_size(queue_uuid):
    max_size = r_serv_metadata.hget('analyzer:{}'.format(queue_uuid), 'max_size')
    if max_size is None:
        max_size = LIST_DEFAULT_SIZE
    return max_size

def get_queue_metadata(queue_uuid, format_type=None, f_date='str_date'):
    dict_queue_meta = {}
    dict_queue_meta['uuid'] = queue_uuid
    dict_queue_meta['size_limit'] = get_queue_max_size(queue_uuid)
    dict_queue_meta['last_updated'] = get_queue_last_seen(queue_uuid, f_date=f_date)

    dict_queue_meta['description'] = r_serv_metadata.hget('analyzer:{}'.format(queue_uuid), 'description')
    if dict_queue_meta['description'] is None:
        dict_queue_meta['description'] = ''

    if format_type:
        dict_queue_meta['length'] = r_serv_analyzer.llen('analyzer:{}:{}'.format(format_type, queue_uuid))
        if dict_queue_meta['length'] is None:
            dict_queue_meta['length'] = 0
    return dict_queue_meta

def edit_queue_description(queue_uuid, description):
    if r_serv_metadata.exists('analyzer:{}'.format(queue_uuid)) and description:
        r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'description', description)

def edit_queue_max_size(queue_uuid, max_size):
    try:
        max_size = int(max_size)
    except:
        return 'analyzer max size, Invalid Integer'

    if r_serv_metadata.exists('analyzer:{}'.format(queue_uuid)) and max_size > 0:
        r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'max_size', max_size)

# create queu by type or by group of uuid
# # TODO: add size limit
def create_queues(format_type, queue_uuid=None, l_uuid=[], queue_type='list', metatype_name=None, description=None):
    queue_uuid = sanitize_uuid(queue_uuid)
    r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'type', format_type)
    edit_queue_description(queue_uuid, description)

    # # TODO: check l_uuid is valid
    if l_uuid:
        analyzer_key_name = 'analyzer_uuid_group'
    else:
        analyzer_key_name = 'analyzer'

    if format_type == 254:
    # TODO: check metatype_name
        r_serv_metadata.sadd('{}:{}:{}'.format(analyzer_key_name, format_type, metatype_name), queue_uuid)
    else:
        r_serv_metadata.sadd('{}:{}'.format(analyzer_key_name, format_type), queue_uuid)

    # Group by UUID
    if l_uuid:
        # # TODO: check sensor_uuid is valid
        for sensor_uuid in l_uuid:
            sensor_uuid = sensor_uuid.replace('-', '')
            r_serv_metadata.sadd('analyzer_sensor_group:{}'.format(queue_uuid), sensor_uuid)
            r_serv_metadata.sadd('sensor:queues:{}:{}'.format(format_type, sensor_uuid), queue_uuid)
    # ALL
    r_serv_metadata.sadd('all_analyzer_queues', queue_uuid)
    return queue_uuid

# format_type int or str (extended type)
def add_data_to_queue(sensor_uuid, format_type, data):
    if data:
        # by data type
        for queue_uuid in get_all_queues_by_type(format_type):
            r_serv_analyzer.lpush('analyzer:{}:{}'.format(format_type, queue_uuid), data)
            r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'last_updated', time.time())
            analyser_queue_max_size = get_queue_max_size(queue_uuid)
            r_serv_analyzer.ltrim('analyzer:{}:{}'.format(format_type, queue_uuid), 0, analyser_queue_max_size)

        # by data type
        for queue_uuid in get_all_queues_by_sensor_group(format_type, sensor_uuid):
            r_serv_analyzer.lpush('analyzer:{}:{}'.format(format_type, queue_uuid), data)
            r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'last_updated', time.time())
            analyser_queue_max_size = get_queue_max_size(queue_uuid)
            r_serv_analyzer.ltrim('analyzer:{}:{}'.format(format_type, queue_uuid), 0, analyser_queue_max_size)


def is_queue_group_of_sensors(queue_uuid):
    if r_serv_metadata.exists('analyzer_sensor_group:{}'.format(queue_uuid)):
        return True
    else:
        return False

def flush_queue(queue_uuid, format_type):
    r_serv_analyzer.delete('analyzer:{}:{}'.format(format_type, queue_uuid))

def remove_queues(queue_uuid, format_type, metatype_name=None):
    if not is_valid_uuid_v4(queue_uuid):
        return {'error': 'Invalid uuid'}

    # delete metadata
    r_serv_metadata.delete('analyzer:{}'.format(queue_uuid))

    # delete queue group of sensors uuid
    l_sensors_uuid = get_queue_group_all_sensors(queue_uuid, r_list=None)
    if l_sensors_uuid:
        r_serv_metadata.delete('analyzer_sensor_group:{}'.format(queue_uuid))
        for sensor_uuid in l_sensors_uuid:
            r_serv_metadata.srem('sensor:queues:{}:{}'.format(format_type, sensor_uuid), queue_uuid)

    if l_sensors_uuid:
        analyzer_key_name = 'analyzer_uuid_group'
    else:
        analyzer_key_name = 'analyzer'

    if format_type == 254:
    # TODO: check metatype_name
        r_serv_metadata.srem('{}:{}:{}'.format(analyzer_key_name, format_type, metatype_name), queue_uuid)
    else:
        r_serv_metadata.srem('{}:{}'.format(analyzer_key_name, format_type), queue_uuid)

    r_serv_metadata.srem('all_analyzer_queues', queue_uuid)

    # delete qeue
    r_serv_analyzer.delete('analyzer:{}:{}'.format(format_type, queue_uuid))

def get_sensor_queues(sensor_uuid):
    pass

if __name__ == '__main__':
    #create_queues(3, l_uuid=['03c00bcf-fe53-46a1-85bb-ee6084cb5bb2'])
    remove_queues('a2e6f95c-1efe-4d2b-a0f5-d8e205d85670', 3)
