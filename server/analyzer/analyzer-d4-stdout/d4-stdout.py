#!/usr/bin/env python3

import os
import sys

import redis
import time
import datetime

import argparse
import logging
import logging.handlers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export d4 data to stdout')
    parser.add_argument('-f', '--files', help='read data from files. trth', action="store_true")
    parser.add_argument('-n', '--newline', help='add new lines', action="store_true")
    parser.add_argument('-t', '--type', help='d4 type' , type=int, dest='type')
    parser.add_argument('-u', '--uuid', help='queue uuid' , type=str, dest='uuid')
    parser.add_argument('-i', '--ip',help='redis host' , type=str, default='127.0.0.1', dest='host_redis')
    parser.add_argument('-p', '--port',help='redis port' , type=int, default=6380, dest='port_redis')
    args = parser.parse_args()

    if not args.uuid or not args.type:
        parser.print_help()
        sys.exit(0)

    host_redis=args.host_redis
    port_redis=args.port_redis
    newLines = args.newline
    read_files = args.files

    redis_d4= redis.StrictRedis(
                        host=host_redis,
                        port=port_redis,
                        db=2)
    try:
        redis_d4.ping()
    except redis.exceptions.ConnectionError:
        print('Error: Redis server {}:{}, ConnectionError'.format(host_redis, port_redis))
        sys.exit(1)

    # logs_dir = 'logs'
    # if not os.path.isdir(logs_dir):
    #     os.makedirs(logs_dir)
    #
    # log_filename = 'logs/d4-stdout.log'
    # logger = logging.getLogger()
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # handler_log = logging.handlers.TimedRotatingFileHandler(log_filename, when="midnight", interval=1)
    # handler_log.suffix = '%Y-%m-%d.log'
    # handler_log.setFormatter(formatter)
    # logger.addHandler(handler_log)
    # logger.setLevel(args.verbose)
    #
    # logger.info('Launching stdout Analyzer ...')

    d4_uuid = args.uuid
    d4_type = args.type

    data_queue = 'analyzer:{}:{}'.format(d4_type, d4_uuid)

    while True:
        d4_data = redis_d4.rpop(data_queue)
        if d4_data is None:
            time.sleep(1)
            continue
        if read_files:
            with open(d4_data, 'rb') as f:
                sys.stdout.buffer.write(f.read())
        else:
            if newLines:
                sys.stdout.buffer.write(d4_data + b'\n')
            else:
                sys.stdout.buffer.write(d4_data)
