#!/usr/bin/env python3

from meta_types_modules.MetaTypesDefault import MetaTypesDefault
import hashlib
import time
import os
import datetime

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
        jsons_save_dir = os.path.join(self.get_save_dir(save_by_uuid=True), 'files')
        if not os.path.isdir(jsons_save_dir):
            os.makedirs(jsons_save_dir)
        # write json file to disk
        m.update(data)
        jsons_path = os.path.join(jsons_save_dir, m.hexdigest()+'.json')
        with open(jsons_path, 'wb') as j:
            j.write(data)
            # Send data to Analyszer
        self.send_to_analyzers(jsons_path)

    def test(self):
        print('Class: filewatcherjson')
