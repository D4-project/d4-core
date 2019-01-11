#!/usr/bin/env python3

import os
import sys
import time
import redis
import subprocess

import datetime

def data_incorrect_format(session_uuid):
    print('Incorrect format')
    sys.exit(1)

redis_server = redis.StrictRedis(
                    host="localhost",
                    port=6379,
                    db=0)

type = 1
tcp_dump_cycle = '5'

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('usage:', 'Worker.py', 'session_uuid')
        exit(1)

    session_uuid = sys.argv[1]
    stream_name = 'stream:{}:{}'.format(type, session_uuid)
    consumer_name = 'consumer:{}:{}'.format(type, session_uuid)
    group_name = 'workers:{}:{}'.format(type, session_uuid)
    id = '0'

    res = redis_server.xread({stream_name: id}, count=1)
    #print(res)
    if res:
        uuid = res[0][1][0][1][b'uuid'].decode()
    else:
        sys.exit(1)
        print('Incorrect message')
    redis_server.sadd('working_session_uuid:{}'.format(type), session_uuid)

    #LAUNCH a tcpdump
    #process = subprocess.Popen(["tcpdump", '-n', '-r', '-', '-G', '5', '-w', '{}/%Y/%m/%d/%H%M%S.cap'.format(uuid)], stdin=subprocess.PIPE)
    process = subprocess.Popen(["tcpdump", '-n', '-r', '-', '-G', tcp_dump_cycle, '-w', '{}-%Y%m%d%H%M%S.cap'.format(uuid)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    #redis_server.xgroup_create('stream:{}:{}'.format(type, session_uuid), 'workers:{}:{}'.format(type, session_uuid))

    while True:
        #print(redis_server.xpending(stream_name, group_name))
        #redis_server.sadd('working_session_uuid:{}'.format(type), session_uuid)

        #res = redis_server.xreadgroup(group_name, consumer_name, {stream_name: '1547198181015-0'}, count=1)
        res = redis_server.xread({stream_name: id}, count=1)
        #print(res)
        if res:
            new_id = res[0][1][0][0].decode()
            if id != new_id:
                id = new_id
                data = res[0][1][0][1]
                if id and data:
                    #print(id)
                    #print(data)

                    #print(data[b'message'])
                    try:
                        process.stdin.write(data[b'message'])
                    except:
                        Error_message = process.stderr.read()
                        if Error_message == b'tcpdump: unknown file format\n':
                            data_incorrect_format(session_uuid)

                        #print(process.stdout.read())

                    #redis_server.xack(stream_name, group_name, id)
                    #redis_server.xdel(stream_name, id)

        else:
            # sucess, all data are saved
            if redis_server.sismember('ended_session', session_uuid):
                out, err = process.communicate(timeout= 0.5)
                #print(out)
                if err == b'tcpdump: unknown file format\n':
                    data_incorrect_format(session_uuid)
                else:
                    print(err)



                #print(process.stderr.read())
                #redis_server.srem('ended_session', session_uuid)
                #redis_server.srem('session_uuid:{}'.format(type), session_uuid)
                #redis_server.srem('working_session_uuid:{}'.format(type), session_uuid)
                #redis_server.delete(stream_name)
                # make sure that tcpdump can save all datas
                print('DONE')
                time.sleep(int(tcp_dump_cycle) + 1)
                print('Exit')
                sys.exit(0)
            else:
                time.sleep(10)
