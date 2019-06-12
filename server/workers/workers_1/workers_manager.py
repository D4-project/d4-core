#!/usr/bin/env python3

import os
import sys
import time
import redis
import subprocess

host_redis_stream = os.getenv('D4_REDIS_STREAM_HOST', "localhost")
port_redis_stream = int(os.getenv('D4_REDIS_STREAM_PORT', 6379))

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0)
type = 1

try:
    redis_server_stream.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server {}:{}, ConnectionError'.format(host_redis_stream, port_redis_stream))
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
