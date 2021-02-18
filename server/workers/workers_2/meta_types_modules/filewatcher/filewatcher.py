#!/usr/bin/env python3

from meta_types_modules.MetaTypesDefault import MetaTypesDefault
import hashlib
import time
import os
import datetime
import base64

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        self.set_rotate_file_mode(False)
        self.saved_dir = ''

    def process_data(self, data):
        self.reconstruct_data(data)

    # pushing the filepath instead of the file content to the analyzer
    def handle_reconstructed_data(self, data):
        m = hashlib.sha256()
        self.set_last_time_saved(time.time())
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

        # Create folder
        save_dir = os.path.join(self.get_save_dir(save_by_uuid=True), 'files')
        #debug_dir = os.path.join(self.get_save_dir(), 'debug')
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        #if not os.path.isdir(debug_dir):
        #    os.makedirs(debug_dir)
        # write binary file to disk
        decodeddata = base64.b64decode(data)
        m.update(decodeddata)
        path  = os.path.join(save_dir, m.hexdigest())
        #pathd  = os.path.join(debug_dir, m.hexdigest())
        with open(path, 'wb') as p:
            p.write(decodeddata)

        #with open(pathd, 'wb') as p:
        #    p.write(data)
            # Send data to Analyszer
        self.send_to_analyzers(path)

    def test(self):
        print('Class: filewatcher')
