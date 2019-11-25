#!/usr/bin/env python3

import os
import sys
import time
import redis
import subprocess

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

### Config ###
config_loader = ConfigLoader.ConfigLoader()
redis_server_stream = config_loader.get_redis_conn("Redis_STREAM", decode_responses=False)
config_loader = None
###  ###

type = 2

try:
    redis_server_stream.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server: Redis_STREAM, ConnectionError')
    sys.exit(1)

if __name__ == "__main__":
    stream_name = 'stream:{}'.format(type)
    redis_server_stream.delete('working_session_uuid:{}'.format(type))

    while True:
        for session_uuid in redis_server_stream.smembers('session_uuid:{}'.format(type)):
            session_uuid = session_uuid.decode()
            if not redis_server_stream.sismember('working_session_uuid:{}'.format(type), session_uuid):

                process = subprocess.Popen(['./worker.py', session_uuid])
                print('Launching new worker{} ...     session_uuid={}'.format(type, session_uuid))

        #print('.')
        time.sleep(10)
