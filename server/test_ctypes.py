#!/usr/bin/env python3
# -*-coding:UTF-8 -*

from ctypes import *

class D4Header(Structure):
    _fields_ = [
        ("version", c_uint8),
        ("type", c_uint8),
        #("uuid", c_uint128),
        ("uuid", c_uint64),
        ("timestamp", c_uint64),
        #("hmac", c_uint256),
        ("hmac", c_uint64),
        ("size", c_uint32),
        ]

def pack(ctype_instance):
    return string_at(byref(ctype_instance), sizeof(ctype_instance))

def unpack(ctype, buffer):
    c_str = create_string_buffer(buffer)
    return cast(pointer(c_str), POINTER(ctype)).contents

if __name__ == '__main__':
    d4h = D4Header(1,1,88888,1543398024,233243445342,342)
    print(d4h.version)
    buffer = pack(d4h)
    print(buffer)
    d = unpack(D4Header, buffer)
    assert(d4h.version == d.version)
