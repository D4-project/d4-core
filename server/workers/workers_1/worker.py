#!/usr/bin/env python3

import os
import sys
import time
import gzip
import redis
import shutil
import datetime
import subprocess
import configparser

def data_incorrect_format(stream_name, session_uuid, uuid):
    redis_server_stream.sadd('Error:IncorrectType', session_uuid)
    redis_server_metadata.hset('metadata_uuid:{}'.format(uuid), 'Error', 'Error: Type={}, Incorrect file format'.format(type))
    clean_stream(stream_name, session_uuid)
    print('Incorrect format, uuid={}'.format(uuid))
    sys.exit(1)

def clean_stream(stream_name, session_uuid):
    redis_server_stream.srem('ended_session', session_uuid)
    redis_server_stream.srem('session_uuid:{}'.format(type), session_uuid)
    redis_server_stream.srem('working_session_uuid:{}'.format(type), session_uuid)
    redis_server_stream.hdel('map-type:session_uuid-uuid:{}'.format(type), session_uuid)
    redis_server_stream.delete(stream_name)

def compress_file(file_full_path, i=0):
    if i==0:
        compressed_filename = '{}.gz'.format(file_full_path)
    else:
        compressed_filename = '{}.{}.gz'.format(file_full_path, i)
    if os.path.isfile(compressed_filename):
        compress_file(file_full_path, i+1)
    else:
        with open(file_full_path, 'rb') as f_in:
            with gzip.open(compressed_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_full_path)
        # save full path in anylyzer queue
        for analyzer_uuid in redis_server_metadata.smembers('analyzer:{}'.format(type)):
            analyzer_uuid = analyzer_uuid.decode()
            redis_server_analyzer.lpush('analyzer:{}:{}'.format(type, analyzer_uuid), compressed_filename)
            redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'last_updated', time.time())
            analyser_queue_max_size = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
            if analyser_queue_max_size is None:
                analyser_queue_max_size = analyzer_list_max_default_size
            redis_server_analyzer.ltrim('analyzer:{}:{}'.format(type, analyzer_uuid), 0, analyser_queue_max_size)

host_redis_stream = os.getenv('D4_REDIS_STREAM_HOST', "localhost")
port_redis_stream = int(os.getenv('D4_REDIS_STREAM_PORT', 6379))

host_redis_metadata = os.getenv('D4_REDIS_METADATA_HOST', "localhost")
port_redis_metadata = int(os.getenv('D4_REDIS_METADATA_PORT', 6380))

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0)

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


type = 1
tcp_dump_cycle = '300'
stream_buffer = 100

analyzer_list_max_default_size = 10000

id_to_delete = []

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('usage:', 'Worker.py', 'session_uuid')
        exit(1)

    session_uuid = sys.argv[1]
    stream_name = 'stream:{}:{}'.format(type, session_uuid)
    id = '0'

    res = redis_server_stream.xread({stream_name: id}, count=1)
    if res:
        uuid = res[0][1][0][1][b'uuid'].decode()
        date = datetime.datetime.now().strftime("%Y%m%d")
        tcpdump_path = os.path.join(data_directory, uuid, str(type))
        full_tcpdump_path = os.path.join(data_directory, uuid, str(type))
        rel_path = os.path.join(tcpdump_path, date[0:4], date[4:6], date[6:8])
        if not os.path.isdir(rel_path):
            os.makedirs(rel_path)
        print('----    worker launched, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
    else:
        sys.exit(1)
        print('Incorrect message')
    redis_server_stream.sadd('working_session_uuid:{}'.format(type), session_uuid)

    #LAUNCH a tcpdump
    process = subprocess.Popen(["tcpdump", '-n', '-r', '-', '-G', tcp_dump_cycle, '-w', '{}/%Y/%m/%d/{}-%Y-%m-%d-%H%M%S.cap'.format(tcpdump_path, uuid)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    nb_save = 0

    process_compressor = subprocess.Popen(['./file_compressor.py', session_uuid, full_tcpdump_path, date])

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
                    new_date = datetime.datetime.now().strftime("%Y%m%d")
                    if new_date != date:
                        date= new_date
                        rel_path = os.path.join(tcpdump_path, date[0:4], date[4:6], date[6:8])
                        if not os.path.isdir(rel_path):
                            os.makedirs(rel_path)

                    try:
                        process.stdin.write(data[b'message'])
                        id_to_delete.append(id)
                    except:
                        Error_message = process.stderr.read()
                        if Error_message == b'tcpdump: unknown file format\n':
                            data_incorrect_format(stream_name, session_uuid, uuid)
                        elif Error_message:
                            print(Error_message)

                        #print(process.stdout.read())
                    nb_save += 1

                    if nb_save > stream_buffer:
                        for id_saved in id_to_delete:
                            redis_server_stream.xdel(stream_name, id_saved)
                        id_to_delete = []
                        nb_save = 0

        else:
            # success, all data are saved
            if redis_server_stream.sismember('ended_session', session_uuid):
                out, err = process.communicate(timeout= 0.5)
                #if out:
                #    print(out)
                if err == b'tcpdump: unknown file format\n':
                    data_incorrect_format(stream_name, session_uuid, uuid)
                elif err:
                    print(err)

                # close child
                try:
                    process_compressor.communicate(timeout= 0.5)
                except subprocess.TimeoutExpired:
                    process_compressor.kill()
                    ### compress all files ###
                    date = datetime.datetime.now().strftime("%Y%m%d")
                    worker_data_directory = os.path.join(full_tcpdump_path, date[0:4], date[4:6], date[6:8])
                    all_files = os.listdir(worker_data_directory)
                    all_files.sort()
                    if all_files:
                        for file in all_files:
                            if file.endswith('.cap'):
                                full_path = os.path.join(worker_data_directory, file)
                                if redis_server_stream.get('data_in_process:{}'.format(session_uuid)) != full_path:
                                    compress_file(full_path)
                    ### ###

                #print(process.stderr.read())
                redis_server_stream.srem('ended_session', session_uuid)
                redis_server_stream.srem('session_uuid:{}'.format(type), session_uuid)
                redis_server_stream.srem('working_session_uuid:{}'.format(type), session_uuid)
                redis_server_stream.hdel('map-type:session_uuid-uuid:{}'.format(type), session_uuid)
                redis_server_stream.delete(stream_name)
                redis_server_stream.delete('data_in_process:{}'.format(session_uuid))
                # make sure that tcpdump can save all datas
                time.sleep(10)
                print('----    tcpdump DONE, uuid={} session_uuid={} epoch={}'.format(uuid, session_uuid, time.time()))
                sys.exit(0)
            else:
                time.sleep(10)
