#!/usr/bin/env python3

import os
import sys
import hmac
import stat
import redis

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol


from ctypes import *
from uuid import UUID

hmac_reset = '0000000000000000000000000000000000000000000000000000000000000000'
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

    if len(data) > 73:

        d4_header = data[:72].hex()
        print(d4_header)
        uuid_header = d4_header[4:36]
        hmac_header = d4_header[64:128]

        d4_header = d4_header.replace(hmac_header, hmac_reset)
        temp = bytes.fromhex(d4_header)
        data = data.replace(data[:72], temp)
        print(data)

        data_header = unpack(D4Header, data)

        ### Debug ###
        print('version: {}'.format( data_header['version'] ))
        print('type: {}'.format( data_header['type'] ))
        print('uuid: {}'.format(uuid_header))
        print('timestamp: {}'.format( data_header['timestamp'] ))
        print('hmac: {}'.format( hmac_header ))
        print('size: {}'.format( data_header['size'] ))
        print('size: {}'.format( len(data) - data_header['struct_size']))
        #print(d4_header)
        ###       ###

        # check if is valid uuid v4
        if not is_valid_uuid_v4(uuid_header):
            print('not uuid v4')
        # verify timestamp
        #elif :
        #    print('not valid timestamp')
        elif data_header['size'] != (len(data) - data_header['struct_size']):
            print('invalid size')
            print('size: {}'.format(data_header['size']))
            print(len(data) - data_header['struct_size']) # sizeof(d)=72
        else:

            # verify hmac sha256
            HMAC = hmac.new(hmac_key, msg=data, digestmod='sha256')
            print('hexdigest: {}'.format( HMAC.hexdigest() ))
            print(data)
            if hmac_header == HMAC.hexdigest():
                print('hmac match')


                redis_server.xadd('stream:{}'.format(data_header['type']), {'message': data[72:], 'uuid':uuid_header, 'timestamp': data_header['timestamp'], 'version': data_header['version']})

                print('END')
                print()
            # discard data
            else:
                print("hmac don't match")
    else:
        print('incomplete data')


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
