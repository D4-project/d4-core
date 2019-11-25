#!/usr/bin/env python3

import os
import sys
import time
import redis

import datetime

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

def data_incorrect_format(session_uuid):
    print('Incorrect format')
    sys.exit(1)

config_loader = ConfigLoader.ConfigLoader()
redis_server_stream = config_loader.get_redis_conn("Redis_STREAM", decode_responses=False)
config_loader = None

# get file config
config_file_server = os.path.join(os.environ['D4_HOME'], 'configs/server.conf')
config_server = configparser.ConfigParser()
config_server.read(config_file_server)

# get data directory
use_default_save_directory = config_loader.get_config_boolean("Save_Directories", "use_default_save_directory")
# check if field is None
if use_default_save_directory:
    data_directory = os.path.join(os.environ['D4_HOME'], 'data')
else:
    data_directory = get_config_str.get_config_boolean("Save_Directories", "save_directory")
config_loader = None

type = 4
rotation_save_cycle = 300 #seconds

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('usage:', 'Worker.py', 'session_uuid')
        exit(1)

    session_uuid = sys.argv[1]
    stream_name = 'stream:{}:{}'.format(type, session_uuid)
    id = '0'

    redis_server_stream.sadd('working_session_uuid:{}'.format(type), session_uuid)

    res = redis_server_stream.xread({stream_name: id}, count=1)
    if res:
        date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        uuid = res[0][1][0][1][b'uuid'].decode()
        data_rel_path = os.path.join(data_directory, uuid, str(type))
        dir_path = os.path.join(data_rel_path, date[0:4], date[4:6], date[6:8])
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        filename = '{}-{}-{}-{}-{}.dnscap.txt'.format(uuid, date[0:4], date[4:6], date[6:8], date[8:14])
        rel_path = os.path.join(dir_path, filename)
        print('----    worker launched, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
    else:
        sys.exit(1)
        print('Incorrect message')

    time_file = time.time()
    rotate_file = False

    while True:

        res = redis_server_stream.xread({stream_name: id}, count=1)
        if res:
            new_id = res[0][1][0][0].decode()
            if id != new_id:
                id = new_id
                data = res[0][1][0][1]
                if id and data:
                    #print(id)
                    #print(data)
                    new_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    if ( new_date[0:8] != date[0:8] ) or ( time.time() - time_file > rotation_save_cycle ):
                        date = new_date
                        rotate_file = True

                    if rotate_file and b'\n[' in data[b'message']:
                        old_str, new_str = data[b'message'].split(b'\n[', maxsplit=1)

                        with open(rel_path, 'ab') as f:
                            f.write(old_str)

                        dir_path = os.path.join(data_rel_path, date[0:4], date[4:6], date[6:8])
                        if not os.path.isdir(dir_path):
                            os.makedirs(dir_path)
                        filename = '{}-{}-{}-{}-{}.dnscap.txt'.format(data[b'uuid'].decode(), date[0:4], date[4:6], date[6:8], date[8:14])
                        rel_path = os.path.join(dir_path, filename)
                        time_file = time.time()
                        rotate_file = False
                        with open(rel_path, 'ab') as f:
                            f.write(b'['+new_str)

                    else:
                        with open(rel_path, 'ab') as f:
                            f.write(data[b'message'])

                    redis_server_stream.xdel(stream_name, id)

        else:
            # sucess, all data are saved
            if redis_server_stream.sismember('ended_session', session_uuid):
                redis_server_stream.srem('ended_session', session_uuid)
                redis_server_stream.srem('session_uuid:{}'.format(type), session_uuid)
                redis_server_stream.srem('working_session_uuid:{}'.format(type), session_uuid)
                redis_server_stream.hdel('map-type:session_uuid-uuid:{}'.format(type), session_uuid)
                redis_server_stream.delete(stream_name)
                print('----    dnscap DONE, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
                sys.exit(0)
            else:
                time.sleep(10)
