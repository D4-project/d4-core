#!/usr/bin/env python3

import sys

from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python import log
from twisted.python.modules import getModule

from twisted.internet.protocol import Protocol

class Echo(Protocol):

    #def __init__(self, factory):
    #    self.factory = factory

    def dataReceived(self, data):
        print(data)
        self.transport.write(data)

def main(reactor):
    log.startLogging(sys.stdout)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(Echo)
    reactor.listenSSL(4443, factory, certificate.options())
    return defer.Deferred()


if __name__ == "__main__":
    task.react(main)
