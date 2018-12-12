#!/usr/bin/env python3

import sys
import hmac

import binascii

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol


from ctypes import *
from uuid import UUID

class Echo(Protocol):

    #def __init__(self, factory):
    #    self.factory = factory

    def dataReceived(self, data):
        print('-----')
        process_header(data)
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

    d4_header = data[:72].hex()
    print(d4_header)

    #version = int(d4_header[0:2], 16)
    #type = int(d4_header[2:4], 16)
    uuid_header = d4_header[4:36]
    #timestamp = d4_header[36:52] fixme
    hmac_header = d4_header[64:128]
    #size = d4_header[128:132] endian issue

    d = unpack(D4Header, data)

    if is_valid_uuid_v4(uuid_header):
        print('version: {}'.format(d.version))
        print('type: {}'.format(d.type))
        print('uuid: {}'.format(uuid_header))
        print('timestamp: {}'.format(d.timestamp))
        print('hmac: {}'.format(hmac_header))
        print('size: {}'.format(d.size))
        print(len(data) - sizeof(d)) # sizeof(d)=72

        print('___________________')
        reset = '0000000000000000000000000000000000000000000000000000000000000000'
        print(d4_header)
        d4_header = d4_header.replace(hmac_header, reset)
        print()
        temp = bytes.fromhex(d4_header)
        data = data.replace(data[:72], temp)
        print(data)


        HMAC = hmac.new(b'private key to change\n', msg=data, digestmod='sha256')
        print(HMAC.digest())
        print(HMAC.hexdigest())
        print(hmac_header)



def unpack(ctype, buffer):
    c_str = create_string_buffer(buffer)
    return cast(pointer(c_str), POINTER(ctype)).contents

def is_valid_uuid_v4(header_uuid):
    #try:
    #print(header_uuid)
    uuid_test = UUID(hex=header_uuid, version=4)
    #print(uuid_test.hex)
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
