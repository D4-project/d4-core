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
from twisted.protocols.policies import TimeoutMixin


from ctypes import *
from uuid import UUID

hmac_reset = bytearray(32)
hmac_key = b'private key to change\n'

redis_server = redis.StrictRedis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=True)

timeout_time = 30

class Echo(Protocol, TimeoutMixin):

    def __init__(self):
        self.buffer = b''
        self.setTimeout(timeout_time)

    def dataReceived(self, data):
        self.resetTimeout()
        self.process_header(data)
        #print(self.transport.client)

    def timeoutConnection(self):
        #print('timeout')
        self.resetTimeout()
        self.buffer = b''
        #self.transport.abortConnection()

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

    def is_valid_uuid_v4(self, header_uuid):
        try:
            uuid_test = UUID(hex=header_uuid, version=4)
            return uuid_test.hex == header_uuid
        except:
            return False

    # # TODO:  check timestamp
    def is_valid_header(self, uuid):
        if self.is_valid_uuid_v4(uuid):
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
                self.buffer += data
                print(self.buffer)
                print(len(self.buffer))
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
        #print('hexdigest: {}'.format( HMAC.hexdigest() ))
        #print('version: {}'.format( data_header['version'] ))
        #print('type: {}'.format( data_header['type'] ))
        #print('uuid: {}'.format(data_header['uuid_header']))
        #print('timestamp: {}'.format( data_header['timestamp'] ))
        #print('hmac: {}'.format( data_header['hmac_header'] ))
        #print('size: {}'.format( data_header['size'] ))
        #print(d4_header)
        ###       ###

        if data_header['hmac_header'] == HMAC.hexdigest():
            #print('hmac match')
            #redis_server.xadd('stream:{}'.format(data_header['type']), {'message': data[62:], 'uuid': data_header['uuid_header'], 'timestamp': data_header['timestamp'], 'version': data_header['version']})
            with open(data_header['uuid_header'], 'ab') as f:
                f.write(data[62:])
        else:
            print('hmac do not match')
            print(data)



def main(reactor):
    log.startLogging(sys.stdout)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(Echo)
    reactor.listenSSL(4443, factory, certificate.options())
    return defer.Deferred()


if __name__ == "__main__":
    task.react(main)
