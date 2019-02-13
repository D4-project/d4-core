#!/usr/bin/env python3

import os
import sys
import time
import gzip
import redis
import shutil
import datetime

import signal

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True

def compress_file(file_full_path, session_uuid,i=0):
    redis_server_stream.set('data_in_process:{}'.format(session_uuid), file_full_path)
    if i==0:
        compressed_filename = '{}.gz'.format(file_full_path)
    else:
        compressed_filename = '{}.{}.gz'.format(file_full_path, i)
    if os.path.isfile(compressed_filename):
        compress_file(file_full_path, session_uuid, i+1)
    else:
        with open(file_full_path, 'rb') as f_in:
            with gzip.open(compressed_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        try:
            os.remove(file_full_path)
        except FileNotFoundError:
            pass
        # save full path in anylyzer queue
        for analyzer_uuid in redis_server_metadata.smembers('analyzer:{}'.format(type)):
            analyzer_uuid = analyzer_uuid.decode()
            redis_server_analyzer.lpush('analyzer:{}:{}'.format(type, analyzer_uuid), compressed_filename)
            redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'last_updated', time.time())
            analyser_queue_max_size = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
            if analyser_queue_max_size is None:
                analyser_queue_max_size = analyzer_list_max_default_size
            redis_server_analyzer.ltrim('analyzer:{}:{}'.format(type, analyzer_uuid), 0, analyser_queue_max_size)


host_redis_stream = "localhost"
port_redis_stream = 6379

host_redis_metadata = "localhost"
port_redis_metadata = 6380

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

type = 1
sleep_time = 300

analyzer_list_max_default_size = 10000

if __name__ == "__main__":
    killer = GracefulKiller()

    if len(sys.argv) != 4:
        print('usage:', 'Worker.py', 'session_uuid', 'tcpdump', 'date')
        exit(1)

    # TODO sanityse input
    session_uuid = sys.argv[1]
    directory_data_uuid = sys.argv[2]
    date = sys.argv[3]

    worker_data_directory = os.path.join(directory_data_uuid, date[0:4], date[4:6], date[6:8])
    full_datetime = datetime.datetime.now().strftime("%Y%m%d%H")

    current_file = None
    time_change = False

    while True:
        if killer.kill_now:
            break

        new_date = datetime.datetime.now().strftime("%Y%m%d")

        # get all directory files
        all_files = os.listdir(worker_data_directory)
        not_compressed_file = []
        # filter: get all not compressed files
        for file in all_files:
            if file.endswith('.cap'):
                not_compressed_file.append(os.path.join(worker_data_directory, file))

        if not_compressed_file:
            ### check time-change (minus one hour) ###
            new_full_datetime = datetime.datetime.now().strftime("%Y%m%d%H")
            if new_full_datetime < full_datetime:
                # sort list, last modified
                not_compressed_file.sort(key=os.path.getctime)
            else:
                # sort list
                not_compressed_file.sort()
            ### ###

            # new day
            if date != new_date:
                # compress all file
                for file in not_compressed_file:
                    if killer.kill_now:
                        break
                    compress_file(file, session_uuid)
                # reset file tracker
                current_file = None
                date = new_date
                # update worker_data_directory
                worker_data_directory = os.path.join(directory_data_uuid, date[0:4], date[4:6], date[6:8])
                # restart
                continue

            # file used by tcpdump
            max_file = not_compressed_file[-1]
            full_datetime = new_full_datetime

            # Init: set current_file
            if not current_file:
                current_file = max_file
                #print('max_file set: {}'.format(current_file))

            # new file created
            if max_file != current_file:

                # get all previous files
                for file in not_compressed_file:
                    if file != max_file:
                        if killer.kill_now:
                            break
                        #print('new file: {}'.format(file))
                        compress_file(file, session_uuid)

                # update current_file tracker
                current_file = max_file

        if killer.kill_now:
            break

        time.sleep(sleep_time)
