#!/usr/bin/env python3

import os
import sys
import uuid
import hmac
import stat
import redis
import struct
import time
import datetime
import argparse
import logging
import logging.handlers

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol
from twisted.protocols.policies import TimeoutMixin

hmac_reset = bytearray(32)
hmac_key = b'private key to change\n'

timeout_time = 30

header_size = 62

data_default_size_limit = 100000

host_redis="localhost"
port_redis=6379
redis_server = redis.StrictRedis(
                    host=host_redis,
                    port=port_redis,
                    db=0)

try:
    redis_server.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server {}:{}, ConnectionError'.format(host_redis, port_redis))
    sys.exit(1)

class Echo(Protocol, TimeoutMixin):

    def __init__(self):
        self.buffer = b''
        self.setTimeout(timeout_time)
        self.session_uuid = str(uuid.uuid4())
        self.data_saved = False
        logger.debug('New session: session_uuid={}'.format(self.session_uuid))

    def dataReceived(self, data):
        self.resetTimeout()
        ip, source_port = self.transport.client
        # check blacklisted_ip
        if redis_server.sismember('blacklist_ip', ip):
            self.transport.abortConnection()
            logger.warning('Blacklisted IP={}, connection closed'.format(ip))

        self.process_header(data, ip, source_port)

    def timeoutConnection(self):
        self.resetTimeout()
        self.buffer = b''
        logger.debug('buffer timeout, session_uuid={}'.format(self.session_uuid))
        #self.transport.abortConnection()

    def connectionLost(self, reason):
            redis_server.sadd('ended_session', self.session_uuid)
            logger.debug('Connection closed: session_uuid={}'.format(self.session_uuid))

    def unpack_header(self, data):
        data_header = {}
        if len(data) >= header_size:
            data_header['version'] = struct.unpack('B', data[0:1])[0]
            data_header['type'] = struct.unpack('B', data[1:2])[0]
            data_header['uuid_header'] = data[2:18].hex()
            data_header['timestamp'] = struct.unpack('Q', data[18:26])[0]
            data_header['hmac_header'] = data[26:58]
            data_header['size'] = struct.unpack('I', data[58:62])[0]

            # uuid blacklist
            if redis_server.sismember('blacklist_uuid', data_header['uuid_header']):
                self.transport.abortConnection()
                logger.warning('Blacklisted UUID={}, connection closed'.format(data_header['uuid_header']))

            # check default size limit
            if data_header['size'] > data_default_size_limit:
                self.transport.abortConnection()
                logger.warning('Incorrect data size: the server received more data than expected by default, expected={}, received={} , uuid={}, session_uuid={}'.format(data_default_size_limit, data_header['size'] ,data_header['uuid_header'], self.session_uuid))

        return data_header

    def is_valid_uuid_v4(self, header_uuid):
        try:
            uuid_test = uuid.UUID(hex=header_uuid, version=4)
            return uuid_test.hex == header_uuid
        except:
            logger.info('Not UUID v4: uuid={}, session_uuid={}'.format(header_uuid, self.session_uuid))
            return False

    # # TODO:  check timestamp
    def is_valid_header(self, uuid_to_check):
        if self.is_valid_uuid_v4(uuid_to_check):
            return True
        else:
            return False

    def process_header(self, data, ip, source_port):
        if not self.buffer:
            data_header = self.unpack_header(data)
            if data_header:
                if self.is_valid_header(data_header['uuid_header']):
                    # check data size
                    if data_header['size'] == (len(data) - header_size):
                        self.process_d4_data(data, data_header, ip)
                    # multiple d4 headers
                    elif data_header['size'] < (len(data) - header_size):
                        next_data = data[data_header['size'] + header_size:]
                        data = data[:data_header['size'] + header_size]
                        #print('------------------------------------------------')
                        #print(data)
                        #print()
                        #print(next_data)
                        self.process_d4_data(data, data_header, ip)
                        # process next d4 header
                        self.process_header(next_data, ip, source_port)
                    # data_header['size'] > (len(data) - header_size)
                    # buffer the data
                    else:
                        #print('**********************************************************')
                        #print(data)
                        #print(data_header['size'])
                        #print((len(data) - header_size))
                        self.buffer += data
                else:
                    if len(data) < header_size:
                        self.buffer += data
                    else:
                        print('discard data')
                        print(data_header)
                        print(data)
                        #time.sleep(5)
                        #sys.exit(1)
            else:
                if len(data) < header_size:
                    self.buffer += data
                    logger.debug('Not enough data received, the header is incomplete, pushing data to buffer, session_uuid={}, data_received={}'.format(self.session_uuid, len(data)))
                else:

                    print('error discard data')
                    print(data_header)
                    print(data)
                    logger.warning('Error unpacking header: incorrect format, session_uuid={}'.format(self.session_uuid))
                    #time.sleep(5)
                    #sys.exit(1)

        # not a header
        else:
            # add previous data
            if len(data) < header_size:
                self.buffer += data
                #print(self.buffer)
                #print(len(self.buffer))
            #todo check if valid header before adding ?
            else:
                data = self.buffer + data
                #print('()()()()()()()()()')
                #print(data)
                #print()
                self.buffer = b''
                self.process_header(data, ip, source_port)

    def process_d4_data(self, data, data_header, ip):
        # empty buffer
        self.buffer = b''
        # set hmac_header to 0
        data = data.replace(data_header['hmac_header'], hmac_reset, 1)
        HMAC = hmac.new(hmac_key, msg=data, digestmod='sha256')
        data_header['hmac_header'] = data_header['hmac_header'].hex()

        ### Debug ###
        #print('hexdigest: {}'.format( HMAC.hexdigest() ))
        #print('version: {}'.format( data_header['version'] ))
        #print('type: {}'.format( data_header['type'] ))
        #print('uuid: {}'.format(data_header['uuid_header']))
        #print('timestamp: {}'.format( data_header['timestamp'] ))
        #print('hmac: {}'.format( data_header['hmac_header'] ))
        #print('size: {}'.format( data_header['size'] ))
        ###       ###

        # hmac match
        if data_header['hmac_header'] == HMAC.hexdigest():
            date = datetime.datetime.now().strftime("%Y%m%d")
            redis_server.xadd('stream:{}:{}'.format(data_header['type'], self.session_uuid), {'message': data[header_size:], 'uuid': data_header['uuid_header'], 'timestamp': data_header['timestamp'], 'version': data_header['version']})
            redis_server.zincrby('stat_uuid_ip:{}:{}'.format(date, data_header['uuid_header']), 1, ip)
            redis_server.zincrby('stat_ip_uuid:{}:{}'.format(date, ip), 1, data_header['uuid_header'])

            redis_server.sadd('daily_uuid:{}'.format(date), data_header['uuid_header'])
            redis_server.sadd('daily_ip:{}'.format(date), ip)

            if not self.data_saved:
                redis_server.sadd('session_uuid:{}'.format(data_header['type']), self.session_uuid.encode())
                redis_server.hset('map-type:session_uuid-uuid:{}'.format(data_header['type']), self.session_uuid, data_header['uuid_header'])
                self.data_saved = True
        else:
            print('hmac do not match')
            print(data)



def main(reactor):
    log.startLogging(sys.stdout)
    try:
        certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    except FileNotFoundError as e:
        print('Error, pem file not found')
        print(e)
        sys.exit(1)
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(Echo)
    reactor.listenSSL(4443, factory, certificate.options())
    return defer.Deferred()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',help='dddd' , type=int, default=30)
    args = parser.parse_args()

    logs_dir = 'logs'
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)

    log_filename = 'logs/d4-server-logs.log'
    logger = logging.getLogger()
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler_log = logging.handlers.TimedRotatingFileHandler(log_filename, when="midnight", interval=1)
    handler_log.suffix = '%Y-%m-%d-{}'.format(log_filename)
    handler_log.setFormatter(formatter)
    logger.addHandler(handler_log)
    logger.setLevel(args.verbose)

    logger.info('Launching Server ...')
    task.react(main)
