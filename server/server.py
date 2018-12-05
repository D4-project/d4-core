#!/usr/bin/env python3

import sys

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol

from ctypes import *

class Echo(Protocol):

    #def __init__(self, factory):
    #    self.factory = factory

    def dataReceived(self, data):
        print(data)
        d = unpack(D4Header, data)
        print('-----')
        print(d.version)
        print(d.type)
        print('{}-{}'.format(d.uuid1, d.uuid2))
        print(d.timestamp)
        print('{}-{}-{}-{}'.format(d.hmac1, d.hmac2, d.hmac3, d.hmac4))
        print(d.size)

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

def unpack(ctype, buffer):
    c_str = create_string_buffer(buffer)
    return cast(pointer(c_str), POINTER(ctype)).contents

def main(reactor):
    log.startLogging(sys.stdout)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(Echo)
    reactor.listenSSL(4443, factory, certificate.options())
    return defer.Deferred()


if __name__ == "__main__":
    task.react(main)
