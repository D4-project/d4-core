#!/usr/bin/env python3

import os
import sys
import time
import redis
import subprocess

redis_server = redis.StrictRedis(
                    host="localhost",
                    port=6379,
                    db=0)
type = 1

try:
    redis_server.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server {}:{}, ConnectionError'.format(host_redis, port_redis))
    sys.exit(1)

if __name__ == "__main__":
    stream_name = 'stream:{}'.format(type)
    redis_server.delete('working_session_uuid:{}'.format(type))

    while True:
        for session_uuid in redis_server.smembers('session_uuid:{}'.format(type)):
            session_uuid = session_uuid.decode()
            if not redis_server.sismember('working_session_uuid:{}'.format(type), session_uuid):

                #try:
                #    redis_server.xgroup_create('stream:{}:{}'.format(type, session_uuid), 'workers:{}:{}'.format(type, session_uuid))
                #xcept redis.exceptions.ResponseError:
                #    pass

                process = subprocess.Popen(['./worker.py', session_uuid])
                print('New worker launched: {}'.format(session_uuid))


        print('sleeping(10)')
        time.sleep(10)
