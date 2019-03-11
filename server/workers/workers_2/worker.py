#!/usr/bin/env python3

import os
import sys
import time
import json
import redis

import datetime

from meta_types_modules import MetaTypesDefault

host_redis_stream = "localhost"
port_redis_stream = 6379

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0)

host_redis_metadata = "localhost"
port_redis_metadata = 6380

redis_server_metadata = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=0)

type_meta_header = 2
type_defined = 254
max_buffer_length = 100000
rotation_save_cycle = 10 #seconds

json_file_name = 'meta_json.json'

def get_class( package_class ):
    parts = package_class.split('.')
    module = ".".join(parts[:-1])
    mod = __import__( module )
    for comp in parts[1:]:
        mod = getattr(mod, comp)
    return mod

def check_default_json_file(json_file):
    # the json object must contain a type field
    if "type" in json_file:
        return True
    else:
        return False

def on_error(session_uuid, type_error, message):
    redis_server_stream.sadd('Error:IncorrectType', session_uuid)
    redis_server_metadata.hset('metadata_uuid:{}'.format(uuid), 'Error', 'Error: Type={}, {}'.format(type_error, message))
    clean_db(session_uuid)
    print('Incorrect format')
    sys.exit(1)

def clean_db(session_uuid):
    clean_stream(stream_meta_json, type_meta_header, session_uuid)
    clean_stream(stream_defined, type_defined, session_uuid)
    redis_server_stream.srem('ended_session', session_uuid)
    redis_server_stream.srem('working_session_uuid:{}'.format(type_meta_header), session_uuid)

def clean_stream(stream_name, type, session_uuid):
    redis_server_stream.srem('session_uuid:{}'.format(type), session_uuid)
    redis_server_stream.hdel('map-type:session_uuid-uuid:{}'.format(type), session_uuid)
    redis_server_stream.delete(stream_name)

if __name__ == "__main__":


    ###################################################3

    if len(sys.argv) != 2:
        print('usage:', 'Worker.py', 'session_uuid')
        exit(1)

    session_uuid = sys.argv[1]
    stream_meta_json = 'stream:{}:{}'.format(type_meta_header, session_uuid)
    stream_defined = 'stream:{}:{}'.format(type_defined, session_uuid)

    id = '0'
    buffer = b''

    stream_name = stream_meta_json
    type = type_meta_header

    # track launched worker
    redis_server_stream.sadd('working_session_uuid:{}'.format(type_meta_header), session_uuid)

    # get uuid
    res = redis_server_stream.xread({stream_name: id}, count=1)
    if res:
        uuid = res[0][1][0][1][b'uuid'].decode()
        print('----    worker launched, uuid={} session_uuid={}'.format(uuid, session_uuid))
    else:
        clean_db(session_uuid)
        print('Incorrect Stream, Closing worker: type={} session_uuid={}'.format(type, session_uuid))
        sys.exit(1)

    full_json = None

    # active session
    while full_json is None:

        res = redis_server_stream.xread({stream_name: id}, count=1)
        if res:
            new_id = res[0][1][0][0].decode()
            if id != new_id:
                id = new_id
                data = res[0][1][0][1]

                if id and data:
                    # remove line from json
                    data[b'message'] = data[b'message'].replace(b'\n', b'')

                    # reconstruct data
                    if buffer != b'':
                        data[b'message'] = b''.join([buffer, data[b'message']])
                        buffer = b''
                    try:
                        full_json = json.loads(data[b'message'].decode())
                    except:
                        buffer += data[b'message']
                        # # TODO: filter too big json
                    redis_server_stream.xdel(stream_name, id)

                    # complete json received
                    if full_json:
                        print(full_json)
                        if check_default_json_file(full_json):
                            # end type 2 processing
                            break
                        # Incorrect Json
                        else:
                            on_error(session_uuid, type, 'Incorrect JSON object')
        else:
            # end session, no json received
            if redis_server_stream.sismember('ended_session', session_uuid):
                clean_db(session_uuid)
                print('----    Incomplete JSON object, DONE, uuid={} session_uuid={}'.format(uuid, session_uuid))
                sys.exit(0)
            else:
                time.sleep(10)

    # extract/parse JSON
    extended_type = full_json['type']
    if not redis_server_metadata.sismember('server:accepted_extended_type', extended_type):
        error_mess = 'Unsupported extended_type: {}'.format(extended_type)
        on_error(session_uuid, type, error_mess)
        clean_db(session_uuid)
        sys.exit(1)


    #### Handle Specific MetaTypes ####
    # Use Specific Handler defined
    if os.path.isdir(os.path.join('meta_types_modules', extended_type)):
        class_type_handler = get_class('meta_types_modules.{}.{}.TypeHandler'.format(extended_type, extended_type))
        type_handler = class_type_handler(uuid, full_json)
    # Use Standard Handler
    else:
        type_handler = MetaTypesDefault.MetaTypesDefault(uuid, full_json)

    #file_separator = type_handler.get_file_separator(self)
    #extended_type_name = type_handler.get_file_name()

    # save json on disk
    type_handler.save_json_file(full_json)

    # change stream_name/type
    stream_name = stream_defined
    type = type_defined
    id = 0
    buffer = b''

    type_handler.test()

    # handle 254 type
    while True:
        res = redis_server_stream.xread({stream_name: id}, count=1)
        if res:
            new_id = res[0][1][0][0].decode()
            if id != new_id:
                id = new_id
                data = res[0][1][0][1]

                if id and data:
                    # process 254 data type
                    type_handler.process_data(data[b'message'])
                    # remove data from redis stream
                    redis_server_stream.xdel(stream_name, id)

        else:
            # end session, no json received
            if redis_server_stream.sismember('ended_session', session_uuid):
                clean_db(session_uuid)
                print('----    JSON object, DONE, uuid={} session_uuid={}'.format(uuid, session_uuid))
                sys.exit(0)
            else:
                time.sleep(10)
