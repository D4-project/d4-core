#!/usr/bin/env python3

import os
import sys

import redis
import time
import datetime

import argparse
import logging
import logging.handlers


import socket



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export d4 data to stdout')
    parser.add_argument('-t', '--type', help='d4 type or extended type' , type=str, dest='type', required=True)
    parser.add_argument('-u', '--uuid', help='queue uuid' , type=str, dest='uuid', required=True)
    parser.add_argument('-i', '--ip',help='server ip' , type=str, default='127.0.0.1', dest='target_ip')
    parser.add_argument('-p', '--port',help='server port' , type=int, dest='target_port', required=True)
    parser.add_argument('-l', '--log_level', help='log level: DEBUG, INFO, WARNING, ERROR, CRITICAL', type=str, default='INFO', dest='req_level')
    parser.add_argument('-n', '--newline', help='add new lines', action="store_true")
    parser.add_argument('-ri', '--redis_ip',help='redis host' , type=str, default='127.0.0.1', dest='host_redis')
    parser.add_argument('-rp', '--redis_port',help='redis port' , type=int, default=6380, dest='port_redis')
    args = parser.parse_args()

    if not args.uuid or not args.type or not args.target_port:
        parser.print_help()
        sys.exit(0)

    host_redis=args.host_redis
    port_redis=args.port_redis
    newLines = args.newline
    req_level = args.req_level

    redis_d4= redis.StrictRedis(
                        host=host_redis,
                        port=port_redis,
                        db=2)
    try:
        redis_d4.ping()
    except redis.exceptions.ConnectionError:
        print('Error: Redis server {}:{}, ConnectionError'.format(host_redis, port_redis))
        sys.exit(1)

    d4_uuid = args.uuid
    d4_type = args.type
    data_queue = 'analyzer:{}:{}'.format(d4_type, d4_uuid)

    target_ip = args.target_ip
    target_port = args.target_port
    addr = (target_ip, target_port)

    #Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    newLines=True
    while True:

        d4_data = redis_d4.rpop(data_queue)
        if d4_data is None:
            time.sleep(1)
            continue

        if newLines:
            d4_data = d4_data + b'\n'

        print(d4_data)
        client_socket.sendto(d4_data, addr)

    client_socket.close()
