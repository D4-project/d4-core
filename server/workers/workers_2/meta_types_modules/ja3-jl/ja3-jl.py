#!/usr/bin/env python3

import os
import sys
import time
import json
import redis

class TypeHandler(MetaTypesDefault:

    def __init__(self, json_file):
        super().__init__(json_file)
        print('init_spec')

    def test2(self):
        print('ja3-jl type')
        print(self.session_uuid)
