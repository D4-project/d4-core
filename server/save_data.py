#!/usr/bin/env python3

import os
import sys
import redis
import time
import gzip
import datetime

redis_server = redis.StrictRedis(
                    host="localhost",
                    port=6379,
                    db=0)

type = 1
max_timestamp = 60*5

def gzip_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    with gzip.open(filepath+'.gz', 'wb') as f2:
        f2.write(content)
    os.remove(filepath)

if __name__ == "__main__":
    stream_name = 'stream:{}'.format(type)

    #group_name = 'group_stream:{}'.format(type)
    #try:
    #    redis_server.xgroup_create(stream_name, group_name)
    #except:
    #    pass

    while True:

        #print(redis_server.xpending(stream_name, group_name))

        #res = redis_server.xreadgroup(group_name, 'consumername', {stream_name: '>'}, count=1)
        res = redis_server.xread({stream_name: '0'}, count=1, block=500)
        if res:
            id = res[0][1][0][0]
            data = res[0][1][0][1]
            if id and data:
                #print(id.decode())
                #print(data)

                date = datetime.datetime.now().strftime("%Y/%m/%d")
                dir_path = os.path.join('data', date, data[b'uuid'].decode())
                filename = ''
                data_timestamp = data[b'timestamp'].decode()

                try:
                    it = os.scandir(dir_path)
                    for entry in it:
                        if not entry.name.endswith(".gz") and entry.is_file():
                            filename = entry.name
                            break
                    filepath = os.path.join(dir_path, filename)

                    if os.path.getsize(filepath) > 500000000: #bytes
                        gzip_file(filepath)
                        filename = data_timestamp

                except FileNotFoundError:
                    os.makedirs(dir_path)
                # # TODO:  use contexte manager in python 3.6
                it = []
                # #

                if not filename:
                    filename = data_timestamp

                if int(data_timestamp) - int(filename) > max_timestamp:
                    gzip_file(filepath)
                    filename = data_timestamp

                with open(os.path.join(dir_path, filename), 'ab') as f:
                    f.write(data[b'message'])

                #redis_server.xack(stream_name, group_name, id)
                redis_server.xdel(stream_name, id)
        else:
            time.sleep(10)
