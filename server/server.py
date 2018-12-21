#!/usr/bin/env python3

import os
import sys
import hmac
import stat
import redis
import struct

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

    #def __init__(self, factory):
    #    self.factory = factory

    def dataReceived(self, data):
        process_header(data)
        print(self.transport.client)
        #print(data[72:])

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
        if hmac_header != HMAC.hexdigest():
            print("hmac don't match ...")
            print('hexdigest: {}'.format( HMAC.hexdigest() ))
            print('hexdigest: {}'.format( hmac_header ))
        ### Debug ###
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
        # verify timestamp
        #elif :
        #    print('not valid timestamp')
        elif size != (len(data) - 62):
            print('invalid size')
            print('size: {}'.format(size))
            print()
            print()
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

'''
def unpack(ctype, buffer):
    c_str = create_string_buffer(buffer)
    d =  cast(pointer(c_str), POINTER(ctype)).contents
    data_header = {}
    data_header['version'] = d.version
    data_header['type'] = d.type
    data_header['timestamp'] = d.timestamp
    data_header['size'] = d.size
    data_header['struct_size'] = sizeof(d)
    return data_header
'''

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
