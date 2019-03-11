#!/usr/bin/env python3

import os
import sys
import time
import json
import redis

from meta_types_modules.MetaTypesDefault import MetaTypesDefault

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        print('init_spec')

    def test(self):
        print('Class: ja3-jl')
