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
    parser.add_argument('-k', '--Keepalive', help='Keepalive in second', type=int, default='15', dest='ka_sec')
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

    # default keep alive: 15
    ka_sec = args.ka_sec

    # Create a TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # TCP Keepalive
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 1)
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, ka_sec)
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, ka_sec)

    # TCP connect
    client_socket.connect(addr)

    newLines=True
    while True:

        d4_data = redis_d4.rpop(data_queue)
        if d4_data is None:
            time.sleep(1)
            continue

        if newLines:
            d4_data = d4_data + b'\n'

        print(d4_data)
        client_socket.sendall(d4_data)

    client_socket.close()
