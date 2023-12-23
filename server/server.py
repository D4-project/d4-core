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

import configparser

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol
from twisted.protocols.policies import TimeoutMixin

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

hmac_reset = bytearray(32)

accepted_type = [1, 2, 4, 8, 254]
accepted_extended_type = ['ja3-jl']

all_server_modes = ('registration', 'shared-secret')

timeout_time = 30

header_size = 62

data_default_size_limit = 1000000
default_max_entries_by_stream = 10000

### Config ###
config_loader = ConfigLoader.ConfigLoader()

# REDIS #
redis_server_stream = config_loader.get_redis_conn("Redis_STREAM", decode_responses=False)
redis_server_metadata = config_loader.get_redis_conn("Redis_METADATA", decode_responses=False)

# get server_mode
try:
    D4server_port = config_loader.get_config_int("D4_Server", "server_port")
except configparser.NoOptionError:
    D4server_port = 4443

server_mode = config_loader.get_config_str("D4_Server", "server_mode")
try:
    hmac_key = config_loader.get_config_str("D4_Server", "default_hmac_key")
except configparser.NoOptionError:
    hmac_key = 'private key to change'

config_loader = None
###  ###

try:
    redis_server_stream.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server Redis_STREAM, ConnectionError')
    sys.exit(1)

try:
    redis_server_metadata.ping()
except redis.exceptions.ConnectionError:
    print('Error: Redis server Redis_METADATA, ConnectionError')
    sys.exit(1)

### REDIS ###

# set hmac default key
redis_server_metadata.set('server:hmac_default_key', hmac_key)

# init redis_server_metadata
for type in accepted_type:
    redis_server_metadata.sadd('server:accepted_type', type)
for type in accepted_extended_type:
    redis_server_metadata.sadd('server:accepted_extended_type', type)

dict_all_connection =  {}

### FUNCTIONS ###

# kick sensors
def kick_sensors():
    for client_uuid in redis_server_stream.smembers('server:sensor_to_kick'):
        client_uuid = client_uuid.decode()
        for session_uuid in redis_server_stream.smembers('map:active_connection-uuid-session_uuid:{}'.format(client_uuid)):
            session_uuid = session_uuid.decode()
            logger.warning('Sensor kicked uuid={}, session_uuid={}'.format(client_uuid, session_uuid))
            redis_server_stream.set('temp_blacklist_uuid:{}'.format(client_uuid), 'some random string')
            redis_server_stream.expire('temp_blacklist_uuid:{}'.format(client_uuid), 30)
            dict_all_connection[session_uuid].transport.abortConnection()
        redis_server_stream.srem('server:sensor_to_kick', client_uuid)

# Unpack D4 Header
#def unpack_header(data):
#    data_header = {}
#    if len(data) >= header_size:
#        data_header['version'] = struct.unpack('B', data[0:1])[0]
#        data_header['type'] = struct.unpack('B', data[1:2])[0]
#        data_header['uuid_header'] = data[2:18].hex()
#        data_header['timestamp'] = struct.unpack('Q', data[18:26])[0]
#        data_header['hmac_header'] = data[26:58]
#        data_header['size'] = struct.unpack('I', data[58:62])[0]
#    return data_header

def is_valid_uuid_v4(header_uuid):
    try:
        uuid_test = uuid.UUID(hex=header_uuid, version=4)
        return uuid_test.hex == header_uuid
    except:
        logger.info('Not UUID v4: uuid={}, session_uuid={}'.format(header_uuid, self.session_uuid))
        return False

# # TODO:  check timestamp
def is_valid_header(uuid_to_check, type):
    if is_valid_uuid_v4(uuid_to_check):
        if redis_server_metadata.sismember('server:accepted_type', type):
            return True
        else:
            logger.warning('Invalid type, the server don\'t accept this type: {}, uuid={}, session_uuid={}'.format(type, uuid_to_check, self.session_uuid))
            return False
    else:
        logger.info('Invalid Header, uuid={}, session_uuid={}'.format(uuid_to_check, self.session_uuid))
        return False

def extract_ip(ip_string):
    #remove interface
    ip_string = ip_string.split('%')[0]
    # IPv4
    #extract ipv4
    if '.' in ip_string:
        return ip_string.split(':')[-1]
    # IPv6
    else:
        return ip_string

def server_mode_registration(header_uuid):
    # only accept registered uuid
    if server_mode == 'registration':
        if not redis_server_metadata.sismember('registered_uuid', header_uuid):
            error_msg = 'Not registered UUID={}, connection closed'.format(header_uuid)
            print(error_msg)
            logger.warning(error_msg)
            #redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: This UUID is temporarily blacklisted')
            return False
        else:
            return True
    else:
        return True

def is_client_ip_blacklisted():
    pass

def is_uuid_blacklisted(uuid):
    return redis_server_metadata.sismember('blacklist_uuid', data_header['uuid_header'])


# return True if not blocked
# False if blacklisted
def check_blacklist():
    pass

# Kill Connection + create log
#def manual_abort_connection(self, message, log_level='WARNING'):
#    logger.log(message)
#    self.transport.abortConnection()
#    return 1

###  ###


class D4_Server(Protocol, TimeoutMixin):

    def __init__(self):
        self.buffer = b''
        self.setTimeout(timeout_time)
        self.session_uuid = str(uuid.uuid4())
        self.data_saved = False
        self.update_stream_type = True
        self.first_connection = True
        self.duplicate = False
        self.ip = None
        self.source_port = None
        self.stream_max_size = None
        self.hmac_key = None
        #self.version = None
        self.type = None
        self.uuid = None
        logger.debug('New session: session_uuid={}'.format(self.session_uuid))
        dict_all_connection[self.session_uuid] = self

    def dataReceived(self, data):
        # check and kick sensor by uuid
        kick_sensors()

        self.resetTimeout()
        if self.first_connection or self.ip is None:
            client_info = self.transport.client
            self.ip = extract_ip(client_info[0])
            self.source_port = client_info[1]
            logger.debug('New connection, ip={}, port={} session_uuid={}'.format(self.ip, self.source_port, self.session_uuid))
        # check blacklisted_ip
        if redis_server_metadata.sismember('blacklist_ip', self.ip):
            self.transport.abortConnection()
            logger.warning('Blacklisted IP={}, connection closed'.format(self.ip))
        else:
            # process data
            self.process_header(data, self.ip, self.source_port)

    def timeoutConnection(self):
        if self.uuid is None:
            # # TODO: ban auto
            logger.warning('Timeout, no D4 header send, session_uuid={}, connection closed'.format(self.session_uuid))
            self.transport.abortConnection()
        else:
            self.resetTimeout()
            self.buffer = b''
            logger.debug('buffer timeout, session_uuid={}'.format(self.session_uuid))

    def connectionMade(self):
        self.transport.setTcpKeepAlive(1)

    def connectionLost(self, reason):
            redis_server_stream.sadd('ended_session', self.session_uuid)
            self.setTimeout(None)

            if not self.duplicate:
                if self.type == 254 or self.type == 2:
                    redis_server_stream.srem('active_uuid_type{}:{}'.format(self.type, self.uuid), self.session_uuid)
                    if not redis_server_stream.exists('active_uuid_type{}:{}'.format(self.type, self.uuid)):
                        redis_server_stream.srem('active_connection:{}'.format(self.type), self.uuid)
                        redis_server_stream.srem('active_connection_by_uuid:{}'.format(self.uuid), self.type)
                    # clean extended type
                    current_extended_type = redis_server_stream.hget('map:session-uuid_active_extended_type', self.session_uuid)
                    if current_extended_type:
                        redis_server_stream.hdel('map:session-uuid_active_extended_type', self.session_uuid)
                        redis_server_stream.srem('active_connection_extended_type:{}'.format(self.uuid), current_extended_type)

                else:
                    if self.uuid:
                        redis_server_stream.srem('active_connection:{}'.format(self.type), self.uuid)
                        redis_server_stream.srem('active_connection_by_uuid:{}'.format(self.uuid), self.type)

            if self.uuid:
                redis_server_stream.srem('map:active_connection-uuid-session_uuid:{}'.format(self.uuid), self.session_uuid)
                if not redis_server_stream.exists('active_connection_by_uuid:{}'.format(self.uuid)):
                    redis_server_stream.srem('active_connection', self.uuid)

            logger.debug('Connection closed: session_uuid={}'.format(self.session_uuid))
            dict_all_connection.pop(self.session_uuid)

    def unpack_header(self, data):
        data_header = {}
        if len(data) >= header_size:
            data_header['version'] = struct.unpack('B', data[0:1])[0]
            data_header['type'] = struct.unpack('B', data[1:2])[0]
            data_header['uuid_header'] = data[2:18].hex()
            data_header['timestamp'] = struct.unpack('Q', data[18:26])[0]
            data_header['hmac_header'] = data[26:58]
            data_header['size'] = struct.unpack('I', data[58:62])[0]
        return data_header

    def check_hmac_key(self, hmac_header, data):
        if self.hmac_key is None:
            self.hmac_key = redis_server_metadata.hget('metadata_uuid:{}'.format(self.uuid), 'hmac_key')
            if self.hmac_key is None:
                self.hmac_key = redis_server_metadata.get('server:hmac_default_key')

        # set hmac_header to 0
        data = data.replace(hmac_header, hmac_reset, 1)

        HMAC = hmac.new(self.hmac_key, msg=data, digestmod='sha256')
        hmac_header = hmac_header.hex()
        # hmac match
        return hmac_header == HMAC.hexdigest()

    def check_connection_validity(self, data_header):
        # blacklist ip by uuid
        if redis_server_metadata.sismember('blacklist_ip_by_uuid', data_header['uuid_header']):
            redis_server_metadata.sadd('blacklist_ip', self.ip)
            self.transport.abortConnection()
            logger.warning('Blacklisted IP by UUID={}, connection closed'.format(data_header['uuid_header']))
            return False

        # uuid blacklist
        if redis_server_metadata.sismember('blacklist_uuid', data_header['uuid_header']):
            logger.warning('Blacklisted UUID={}, connection closed'.format(data_header['uuid_header']))
            self.transport.abortConnection()
            return False

        # Check server mode
        if not server_mode_registration(data_header['uuid_header']):
            self.transport.abortConnection()
            return False

        # check temp blacklist
        if redis_server_stream.exists('temp_blacklist_uuid:{}'.format(data_header['uuid_header'])):
            logger.warning('Temporarily Blacklisted UUID={}, connection closed'.format(data_header['uuid_header']))
            redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: This UUID is temporarily blacklisted')
            self.transport.abortConnection()
            return False

        # check default size limit
        if data_header['size'] > data_default_size_limit:
            self.transport.abortConnection()
            logger.warning('Incorrect header data size: the server received more data than expected by default, expected={}, received={} , uuid={}, session_uuid={}'.format(data_default_size_limit, data_header['size'] ,data_header['uuid_header'], self.session_uuid))
            return False

        # Worker: Incorrect type
        if redis_server_stream.sismember('Error:IncorrectType', self.session_uuid):
            self.transport.abortConnection()
            redis_server_stream.delete('stream:{}:{}'.format(data_header['type'], self.session_uuid))
            redis_server_stream.srem('Error:IncorrectType', self.session_uuid)
            logger.warning('Incorrect type={} detected by worker, uuid={}, session_uuid={}'.format(data_header['type'] ,data_header['uuid_header'], self.session_uuid))
            return False

        return True

    def process_header(self, data, ip, source_port):
        if not self.buffer:
            data_header = self.unpack_header(data)
            if data_header:
                if not self.check_connection_validity(data_header):
                    return 1
                if is_valid_header(data_header['uuid_header'], data_header['type']):

                    # auto kill connection # TODO: map type
                    if self.first_connection:
                        self.first_connection = False
                        if data_header['type'] == 2:
                            redis_server_stream.sadd('active_uuid_type2:{}'.format(data_header['uuid_header']), self.session_uuid)

                        # type 254, check if previous type 2 saved
                        elif data_header['type'] == 254:
                            logger.warning('a type 2 packet must be sent, ip={} uuid={} type={} session_uuid={}'.format(ip, data_header['uuid_header'], data_header['type'], self.session_uuid))
                            redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: a type 2 packet must be sent, type={}'.format(data_header['type']))
                            self.duplicate = True
                            self.transport.abortConnection()
                            return 1

                        # accept only one type/by uuid (except for type 2/254)
                        elif redis_server_stream.sismember('active_connection:{}'.format(data_header['type']), '{}'.format(data_header['uuid_header'])):
                            # same IP-type for an UUID
                            logger.warning('is using the same UUID for one type, ip={} uuid={} type={} session_uuid={}'.format(ip, data_header['uuid_header'], data_header['type'], self.session_uuid))
                            redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: This UUID is using the same UUID for one type={}'.format(data_header['type']))
                            self.duplicate = True
                            self.transport.abortConnection()
                            return 1

                        self.type = data_header['type']
                        self.uuid = data_header['uuid_header']

                        # # check HMAC /!\ incomplete data
                        # if not self.check_hmac_key(data_header['hmac_header'], data):
                        #     print('hmac do not match')
                        #     print(data)
                        #     logger.debug("HMAC don't match, uuid={}, session_uuid={}".format(self.uuid, self.session_uuid))
                        #     redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: HMAC don\'t match')
                        #     self.transport.abortConnection()
                        #     return 1

                        ## save active connection ##
                        #active Connection
                        redis_server_stream.sadd('active_connection:{}'.format(self.type), self.uuid)
                        redis_server_stream.sadd('active_connection_by_uuid:{}'.format(self.uuid), self.type)
                        redis_server_stream.sadd('active_connection', self.uuid)
                        # map session_uuid/uuid
                        redis_server_stream.sadd('map:active_connection-uuid-session_uuid:{}'.format(self.uuid), self.session_uuid)

                        # map all type by uuid ## TODO: # FIXME:  put me in workers ??????
                        redis_server_metadata.sadd('all_types_by_uuid:{}'.format(data_header['uuid_header']), data_header['type'])
                        ## ##

                    # check if type change
                    if self.data_saved:
                        # type change detected
                        if self.type != data_header['type']:
                            # Meta types
                            if self.type == 2 and data_header['type'] == 254:
                                self.update_stream_type = True
                                self.type = data_header['type']
                                #redis_server_stream.hdel('map-type:session_uuid-uuid:2', self.session_uuid) # # TODO:  to remove / refractor
                                redis_server_stream.srem('active_uuid_type2:{}'.format(self.uuid), self.session_uuid)

                                # remove type 2 connection
                                if not redis_server_stream.exists('active_uuid_type2:{}'.format(self.uuid)):
                                    redis_server_stream.srem('active_connection:2', self.uuid)
                                    redis_server_stream.srem('active_connection_by_uuid:{}'.format(self.uuid), 2)

                                ## save active connection ##
                                #active Connection
                                redis_server_stream.sadd('active_connection:{}'.format(self.type), self.uuid)
                                redis_server_stream.sadd('active_connection_by_uuid:{}'.format(self.uuid), self.type)
                                redis_server_stream.sadd('active_connection', self.uuid)

                                redis_server_stream.sadd('active_uuid_type254:{}'.format(self.uuid), self.session_uuid)

                                # map all type by uuid ## TODO: # FIXME:  put me in workers ??????
                                redis_server_metadata.sadd('all_types_by_uuid:{}'.format(data_header['uuid_header']), data_header['type'])
                                ## ##


                                #redis_server_stream.hset('map-type:session_uuid-uuid:{}'.format(data_header['type']), self.session_uuid, data_header['uuid_header'])


                            # Type Error
                            else:
                                logger.warning('Unexpected type change, type={} new type={}, ip={} uuid={} session_uuid={}'.format(ip, data_header['uuid_header'], data_header['type'], self.session_uuid))
                                redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: Unexpected type change type={}, new type={}'.format(self.type, data_header['type']))
                                self.transport.abortConnection()
                                return 1

                    # check if the uuid is the same
                    if self.uuid != data_header['uuid_header']:
                        logger.warning('The uuid change during the connection, ip={} uuid={} type={} session_uuid={} new_uuid={}'.format(ip, self.uuid, data_header['type'], self.session_uuid, data_header['uuid_header']))
                        redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: The uuid change, new_uuid={}'.format(data_header['uuid_header']))
                        self.transport.abortConnection()
                        return 1
                        ## TODO: ban ?

                    # check data size
                    if data_header['size'] == (len(data) - header_size):
                        res = self.process_d4_data(data, data_header, ip)
                        # Error detected, kill connection
                        if res == 1:
                            return 1
                    # multiple d4 headers
                    elif data_header['size'] < (len(data) - header_size):
                        next_data = data[data_header['size'] + header_size:]
                        data = data[:data_header['size'] + header_size]
                        #print('------------------------------------------------')
                        #print(data)
                        #print()
                        #print(next_data)
                        res = self.process_d4_data(data, data_header, ip)
                        # Error detected, kill connection
                        if res == 1:
                            return 1
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
                        logger.warning('Invalid Header, uuid={}, session_uuid={}'.format(data_header['uuid_header'], self.session_uuid))
            else:
                if len(data) < header_size:
                    self.buffer += data
                    #logger.debug('Not enough data received, the header is incomplete, pushing data to buffer, session_uuid={}, data_received={}'.format(self.session_uuid, len(data)))
                else:

                    print('error discard data')
                    print(data_header)
                    print(data)
                    logger.warning('Error unpacking header: incorrect format, session_uuid={}'.format(self.session_uuid))

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
        if self.check_hmac_key(data_header['hmac_header'], data):
            if not self.stream_max_size:
                temp = redis_server_metadata.hget('stream_max_size_by_uuid', data_header['uuid_header'])
                if temp is not None:
                    self.stream_max_size = int(temp)
                else:
                    self.stream_max_size = default_max_entries_by_stream

            date = datetime.datetime.now().strftime("%Y%m%d")
            if redis_server_stream.xlen('stream:{}:{}'.format(data_header['type'], self.session_uuid)) < self.stream_max_size:
                # Clean Error Message
                redis_server_metadata.hdel('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error')

                redis_server_stream.xadd('stream:{}:{}'.format(data_header['type'], self.session_uuid), {'message': data[header_size:], 'uuid': data_header['uuid_header'], 'timestamp': data_header['timestamp'], 'version': data_header['version']})

                # daily stats
                redis_server_metadata.zincrby('stat_uuid_ip:{}:{}'.format(date, data_header['uuid_header']), 1, ip)
                redis_server_metadata.zincrby('stat_ip_uuid:{}:{}'.format(date, ip), 1, data_header['uuid_header'])
                redis_server_metadata.zincrby('daily_uuid:{}'.format(date), 1, data_header['uuid_header'])
                redis_server_metadata.zincrby('daily_ip:{}'.format(date), 1, ip)
                redis_server_metadata.zincrby('daily_type:{}'.format(date), 1, data_header['type'])
                redis_server_metadata.zincrby('stat_type_uuid:{}:{}'.format(date, data_header['type']), 1, data_header['uuid_header'])
                redis_server_metadata.zincrby('stat_uuid_type:{}:{}'.format(date, data_header['uuid_header']), 1, data_header['type'])

                #
                d4_packet_rcv_time = int(time.time())
                if not redis_server_metadata.hexists('metadata_uuid:{}'.format(data_header['uuid_header']), 'first_seen'):
                    redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'first_seen', d4_packet_rcv_time)
                redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'last_seen', d4_packet_rcv_time)
                redis_server_metadata.hset('metadata_type_by_uuid:{}:{}'.format(data_header['uuid_header'], data_header['type']), 'last_seen', d4_packet_rcv_time)

                if not self.data_saved:
                    # worker entry point: map type:session_uuid
                    redis_server_stream.sadd('session_uuid:{}'.format(data_header['type']), self.session_uuid.encode())

                    #UUID IP:           ## TODO: use d4 timestamp ?
                    redis_server_metadata.lpush('list_uuid_ip:{}'.format(data_header['uuid_header']), '{}-{}'.format(ip, datetime.datetime.now().strftime("%Y%m%d%H%M%S")))
                    redis_server_metadata.ltrim('list_uuid_ip:{}'.format(data_header['uuid_header']), 0, 15)

                    self.data_saved = True
                if self.update_stream_type:

                    if not redis_server_metadata.hexists('metadata_type_by_uuid:{}:{}'.format(data_header['uuid_header'], data_header['type']), 'first_seen'):
                        redis_server_metadata.hset('metadata_type_by_uuid:{}:{}'.format(data_header['uuid_header'], data_header['type']), 'first_seen', d4_packet_rcv_time)
                    self.update_stream_type = False
                return 0
            else:
                logger.warning("stream exceed max entries limit, uuid={}, session_uuid={}, type={}".format(data_header['uuid_header'], self.session_uuid, data_header['type']))
                ## TODO: FIXME
                redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: stream exceed max entries limit')

                self.transport.abortConnection()
                return 1
        else:
            print('hmac do not match')
            print(data)
            logger.debug("HMAC don't match, uuid={}, session_uuid={}".format(data_header['uuid_header'], self.session_uuid))
            ## TODO: FIXME
            redis_server_metadata.hset('metadata_uuid:{}'.format(data_header['uuid_header']), 'Error', 'Error: HMAC don\'t match')
            self.transport.abortConnection()
            return 1


def main(reactor):
    log.startLogging(sys.stdout)
    try:
        certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    except FileNotFoundError as e:
        print('Error, pem file not found')
        print(e)
        sys.exit(1)
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(D4_Server)
    # use interface to support both IPv4 and IPv6
    reactor.listenSSL(D4server_port, factory, certificate.options(), interface='::')
    return defer.Deferred()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',help='dddd' , type=int, default=30)
    args = parser.parse_args()

    if not redis_server_metadata.exists('first_date'):
        redis_server_metadata.set('first_date', datetime.datetime.now().strftime("%Y%m%d"))

    logs_dir = 'logs'
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)

    log_filename = 'logs/d4-server.log'
    logger = logging.getLogger()
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler_log = logging.handlers.TimedRotatingFileHandler(log_filename, when="midnight", interval=1)
    handler_log.suffix = '%Y-%m-%d.log'
    handler_log.setFormatter(formatter)
    logger.addHandler(handler_log)
    logger.setLevel(args.verbose)

    # get server_mode
    if server_mode not in all_server_modes:
        print('Error: incorrect server_mode')
        logger.critical('Error: incorrect server_mode')
        sys.exit(1)
    logger.info('Server mode: {}'.format(server_mode))


    logger.info('Launching Server ...')

    task.react(main)
