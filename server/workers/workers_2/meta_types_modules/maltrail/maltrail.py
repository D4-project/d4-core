#!/usr/bin/env python3

from meta_types_modules.MetaTypesDefault import MetaTypesDefault

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        self.set_rotate_file_mode(False)
        self.saved_dir = ''

    def process_data(self, data):
        self.reconstruct_data(data)

    def test(self):
        print('Class: maltrail')
