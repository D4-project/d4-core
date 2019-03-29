#!/usr/bin/env python3

import os
import sys
import time
import redis

import datetime
import configparser

def data_incorrect_format(session_uuid):
    print('Incorrect format')
    sys.exit(1)

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

redis_server_analyzer = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=2)

# get file config
config_file_server = os.path.join(os.environ['D4_HOME'], 'configs/server.conf')
config_server = configparser.ConfigParser()
config_server.read(config_file_server)

# get data directory
use_default_save_directory = config_server['Save_Directories'].getboolean('use_default_save_directory')
# check if field is None
if use_default_save_directory:
    data_directory = os.path.join(os.environ['D4_HOME'], 'data')
else:
    data_directory = config_server['Save_Directories'].get('save_directory')


type = 8
rotation_save_cycle = 300 #seconds

analyzer_list_max_default_size = 10000

max_buffer_length = 10000

save_to_file = True

def get_save_dir(dir_data_uuid, year, month, day):
    dir_path = os.path.join(dir_data_uuid, year, month, day)
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    return dir_path

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('usage:', 'Worker.py', 'session_uuid')
        exit(1)

    session_uuid = sys.argv[1]
    stream_name = 'stream:{}:{}'.format(type, session_uuid)
    id = '0'
    buffer = b''

    # track launched worker
    redis_server_stream.sadd('working_session_uuid:{}'.format(type), session_uuid)

    # get uuid
    res = redis_server_stream.xread({stream_name: id}, count=1)
    if res:
        uuid = res[0][1][0][1][b'uuid'].decode()
        # init file rotation
        if save_to_file:
            rotate_file = False
            time_file = time.time()
            date_file = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dir_data_uuid = os.path.join(data_directory, uuid, str(type))
            dir_full_path = get_save_dir(dir_data_uuid, date_file[0:4], date_file[4:6], date_file[6:8])
            filename = '{}-{}-{}-{}-{}.passivedns.txt'.format(uuid, date_file[0:4], date_file[4:6], date_file[6:8], date_file[8:14])
            save_path = os.path.join(dir_full_path, filename)

        print('----    worker launched, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
    else:
        ########################### # TODO: clean db on error
        print('Incorrect Stream, Closing worker: type={} session_uuid={}'.format(type, session_uuid))
        sys.exit(1)

    while True:

        res = redis_server_stream.xread({stream_name: id}, count=1)
        if res:
            new_id = res[0][1][0][0].decode()
            if id != new_id:
                id = new_id
                data = res[0][1][0][1]

                if id and data:
                    # reconstruct data
                    if buffer != b'':
                        data[b'message'] = b''.join(buffer, data[b'message'])
                        buffer = b''

                    # send data to redis
                    # new line in received data
                    if b'\n' in data[b'message']:
                        all_line = data[b'message'].split(b'\n')
                        for line in all_line[:-1]:
                            for analyzer_uuid in redis_server_metadata.smembers('analyzer:{}'.format(type)):
                                analyzer_uuid = analyzer_uuid.decode()
                                redis_server_analyzer.lpush('analyzer:{}:{}'.format(type, analyzer_uuid), line)
                                redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'last_updated', time.time())
                                analyser_queue_max_size = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
                                if analyser_queue_max_size is None:
                                    analyser_queue_max_size = analyzer_list_max_default_size
                                redis_server_analyzer.ltrim('analyzer:{}:{}'.format(type, analyzer_uuid), 0, analyser_queue_max_size)
                        # keep incomplete line
                        if all_line[-1] != b'':
                            buffer += all_line[-1]
                    else:
                        if len(buffer) < max_buffer_length:
                            buffer += data[b'message']
                        else:
                            print('Error, infinite loop, max buffer length reached')
                            # force new line
                            buffer += b''.join([ data[b'message'], b'\n' ])


                    # save data on disk
                    if save_to_file:
                        new_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        # check if a new rotation is needed
                        if ( new_date[0:8] != date_file[0:8] ) or ( time.time() - time_file > rotation_save_cycle ):
                            date_file = new_date
                            rotate_file = True

                        # file rotation
                        if rotate_file and b'\n' in data[b'message']:
                            end_file, start_new_file = data[b'message'].rsplit(b'\n', maxsplit=1)
                            # save end of file
                            with open(save_path, 'ab') as f:
                                f.write(end_file)

                            # get new save_path
                            dir_full_path = get_save_dir(dir_data_uuid, date_file[0:4], date_file[4:6], date_file[6:8])
                            filename = '{}-{}-{}-{}-{}.passivedns.txt'.format(uuid, date_file[0:4], date_file[4:6], date_file[6:8], date_file[8:14])
                            save_path = os.path.join(dir_full_path, filename)

                            # save start of new file
                            if start_new_file != b'':
                                with open(save_path, 'ab') as f:
                                    f.write(start_new_file)
                            # end of rotation
                            rotate_file = False
                            time_file = time.time()

                        else:
                            with open(save_path, 'ab') as f:
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
                print('----    passivedns DONE, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
                sys.exit(0)
            else:
                time.sleep(10)
