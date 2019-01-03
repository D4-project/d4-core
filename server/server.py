#!/usr/bin/env python3

import os
import sys
import hmac
import stat
import redis
import struct
import time

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol


from ctypes import *
from uuid import UUID

hmac_reset = bytearray(32)
hmac_key = b'private key to change\n'

redis_server = redis.StrictRedis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=True)

class Echo(Protocol):

    def __init__(self):
        self.buffer = b''

    def dataReceived(self, data):
        self.process_header(data)
        print(self.transport.client)
        #print(data[72:])

    #def timeoutConnection(self):
    #    self.transport.abortConnection()

    def unpack_header(self, data):
        data_header = {}
        if len(data) > 62:
            data_header['version'] = struct.unpack('B', data[0:1])[0]
            data_header['type'] = struct.unpack('B', data[1:2])[0]
            data_header['uuid_header'] = data[2:18].hex()
            data_header['timestamp'] = struct.unpack('Q', data[18:26])[0]
            data_header['hmac_header'] = data[26:58]
            data_header['size'] = struct.unpack('I', data[58:62])[0]

        return data_header

    # # TODO:  check timestamp
    def is_valid_header(self, uuid):
        if is_valid_uuid_v4(uuid):
            return True
        else:
            return False

    def process_header(self, data):
        if not self.buffer:
            data_header = self.unpack_header(data)
            if data_header:
                if self.is_valid_header(data_header['uuid_header']):
                    # check data size
                    if data_header['size'] == (len(data) - 62):
                        self.process_d4_data(data, data_header)
                    # multiple d4 headers
                    elif data_header['size'] < (len(data) - 62):
                        next_data = data[data_header['size'] + 62:]
                        data = data[:data_header['size'] + 62]
                        #print('------------------------------------------------')
                        #print(data)
                        #print()
                        #print(next_data)
                        self.process_d4_data(data, data_header)
                        # process next d4 header
                        self.process_header(next_data)
                    # data_header['size'] > (len(data) - 62)
                    # buffer the data
                    else:
                        #print('**********************************************************')
                        #print(data)
                        #print(data_header['size'])
                        #print((len(data) - 62))
                        self.buffer += data
                else:
                    if len(data) < 62:
                        self.buffer += data
                    else:
                        print('discard data')
                        print(data_header)
                        print(data)
                        time.sleep(5)
                        #sys.exit(1)
            else:
                if len(data) < 62:
                    self.buffer += data
                else:
                    print('error discard data')
                    print(data_header)
                    print(data)
                    time.sleep(5)
                    #sys.exit(1)

        # not a header
        else:
            # add previous data
            if len(data) < 62:
                data = self.buffer + data
                print(data)
                print()
            #todo check if valid header before adding ?
            else:
                data = self.buffer + data
                #print('()()()()()()()()()')
                #print(data)
                #print()
                self.buffer = b''
                self.process_header(data)

    def process_d4_data(self, data, data_header):
        # empty buffer
        self.buffer = b''
        # set hmac_header to 0
        data = data.replace(data_header['hmac_header'], hmac_reset, 1)
        HMAC = hmac.new(hmac_key, msg=data, digestmod='sha256')
        data_header['hmac_header'] = data_header['hmac_header'].hex()

        ### Debug ###
        print('hexdigest: {}'.format( HMAC.hexdigest() ))
        print('version: {}'.format( data_header['version'] ))
        print('type: {}'.format( data_header['type'] ))
        print('uuid: {}'.format(data_header['uuid_header']))
        print('timestamp: {}'.format( data_header['timestamp'] ))
        print('hmac: {}'.format( data_header['hmac_header'] ))
        print('size: {}'.format( data_header['size'] ))
        #print(d4_header)
        ###       ###

        if data_header['hmac_header'] == HMAC.hexdigest():
            print('hmac match')
        else:
            print('hmac do not match')
        print()


class D4Header(Structure):
    _fields_ = [
        ("version", c_uint8),
        ("type", c_uint8),
        ("uuid1", c_uint64),
        ("uuid2", c_uint64),
        ("timestamp", c_uint64),
        ("hmac1", c_uint64),
        ("hmac2", c_uint64),
        ("hmac3", c_uint64),
        ("hmac4", c_uint64),
        ("size", c_uint32),
        ]

def process_header(data):

    if len(data) > 63:

        d4_header = data[:62]
        all_data = data[62:]
        #print(d4_header)

        version = struct.unpack('B', d4_header[0:1])[0]
        type = struct.unpack('B', d4_header[1:2])[0]
        uuid_header = d4_header[2:18].hex()
        timestamp = struct.unpack('Q', d4_header[18:26])[0]
        hmac_header = d4_header[26:58]
        size = struct.unpack('I', d4_header[58:62])[0]

        print('-------------------------')
        print(hmac_header)
        print(hmac_reset)
        print('***************************')
        print(d4_header)
        d4_header = d4_header.replace(hmac_header, hmac_reset)

        print(d4_header)
        data = d4_header + all_data
        print(data)
        #print(data[:62])
        #print(len(data[:62]))

        hmac_header = hmac_header.hex()

        # verify hmac sha256
        HMAC = hmac.new(hmac_key, msg=data, digestmod='sha256')
        print('hexdigest: {}'.format( HMAC.hexdigest() ))
        #print(data)
        #if hmac_header != HMAC.hexdigest():
        #    print("hmac don't match ...")
        #    print('hexdigest: {}'.format( HMAC.hexdigest() ))
        #    print('hexdigest: {}'.format( hmac_header ))
        ### Debug ###
        #print(data)
        print('version: {}'.format( version ))
        print('type: {}'.format( type ))
        print('uuid: {}'.format(uuid_header))
        print('timestamp: {}'.format( timestamp ))
        print('hmac: {}'.format( hmac_header ))
        print('size: {}'.format( size ))
        #print(d4_header)
        ###       ###

        # check if is valid uuid v4
        if not is_valid_uuid_v4(uuid_header):
            print('not uuid v4')
            print()
            print()
            sys.exit(1)

        # verify timestamp
        #elif :
        #    print('not valid timestamp')
        elif size != (len(data) - 62):
            print('invalid size')
            print('size: {}, expected size: {}'.format(len(data) - 62, size))
            print()
            print()
            print(data[:size])
            print()
            print()
            print(data[size:])
            sys.exit(1)
        else:

            # verify hmac sha256
            HMAC = hmac.new(hmac_key, msg=data, digestmod='sha256')
            print('hexdigest: {}'.format( HMAC.hexdigest() ))
            #print(data)
            if hmac_header == HMAC.hexdigest():
                print('hmac match')


                #redis_server.xadd('stream:{}'.format(data_header['type']), {'message': data[72:], 'uuid':uuid_header, 'timestamp': data_header['timestamp'], 'version': data_header['version']})

                print('END')
                print()
            # discard data
            else:
                print("hmac don't match")
                print()
                print()
    else:
        print('incomplete data')
        print()
        print()


def is_valid_uuid_v4(header_uuid):
    #try:
    uuid_test = UUID(hex=header_uuid, version=4)
    return uuid_test.hex == header_uuid
    #except:
    #    return False

def main(reactor):
    log.startLogging(sys.stdout)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(Echo)
    reactor.listenSSL(4443, factory, certificate.options())
    return defer.Deferred()


if __name__ == "__main__":
    task.react(main)
