#!/usr/bin/env python3

from meta_types_modules.MetaTypesDefault import MetaTypesDefault
import hashlib
import time
import os
import datetime
import base64
import shutil
import gzip

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        self.compress = False
        self.extension = ''
        self.segregate = True
        if "compress" in json_file:
            self.compress = json_file['compress']
        if "extension" in json_file:
            self.extension = json_file['extension']
        if "segregate" in json_file:
            self.segregate = json_file['segregate']
        self.set_rotate_file_mode(False)
        self.saved_dir = ''

    def process_data(self, data):
        # Unpack the thing
        self.reconstruct_data(data)

    # pushing the filepath instead of the file content to the analyzer
    def handle_reconstructed_data(self, data):
        m = hashlib.sha256()
        self.set_last_time_saved(time.time())
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

        # Create folder
        save_dir = os.path.join(self.get_save_dir(save_by_uuid=self.segregate), 'files')
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        # write file to disk
        decodeddata = base64.b64decode(data)

        m.update(decodeddata)
        path  = os.path.join(save_dir, m.hexdigest())
        path = '{}.{}'.format(path, self.extension)
        with open(path, 'wb') as p:
            p.write(decodeddata)
        if self.compress:
            compressed_filename = '{}.gz'.format(path)
            with open(path, 'rb') as f_in:
                with gzip.open(compressed_filename, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(path)
            self.send_to_analyzers(compressed_filename)
        else:
            self.send_to_analyzers(path)

    def reconstruct_data(self, data):
        # save data in buffer
        self.add_to_buffer(data)
        data = self.get_buffer()

        # end of element found in data
        if self.get_file_separator() in data:
            # empty buffer
            self.reset_buffer()
            all_line = data.split(self.get_file_separator())
            for reconstructed_data in all_line[:-1]:
                if reconstructed_data != b'':
                    self.handle_reconstructed_data(reconstructed_data)

            # save incomplete element in buffer
            if all_line[-1] != b'':
                self.add_to_buffer(all_line[-1])


def test(self):
        print('Class: filewatcher')