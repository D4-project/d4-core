#!/usr/bin/env python3

import os
import sys
import time
import json
import redis
import datetime
import hashlib
import binascii
import redis
import pdb

from meta_types_modules.MetaTypesDefault import MetaTypesDefault

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        self.set_rotate_file_mode(False)

    def process_data(self, data):
        self.reconstruct_data(data)

    def handle_reconstructed_data(self, data):
        decoded_data = data.decode()
        self.set_last_time_saved(time.time())
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

        # Create folders
        cert_save_dir = os.path.join(self.get_save_dir(), 'certs')
        jsons_save_dir = os.path.join(self.get_save_dir(), 'jsons')
        if not os.path.isdir(cert_save_dir):
            os.makedirs(cert_save_dir)
        if not os.path.isdir(jsons_save_dir):
            os.makedirs(jsons_save_dir)

        # Extract certificates from json
        try:
            mtjson = json.loads(decoded_data)
            res = True
        except Exception as e:
            print(decoded_data)
            res = False
        if res:
            #mtjson = json.loads(decoded_data)
            for certificate in mtjson["Certificates"] or []:
                cert = binascii.a2b_base64(certificate["Raw"])
                # one could also load this cert with
                # xcert = x509.load_der_x509_certificate(cert, default_backend())
                m = hashlib.sha1()
                m.update(cert)
                cert_path = os.path.join(cert_save_dir, m.hexdigest()+'.crt')
                # write unique certificate der file to disk
                with open(cert_path, 'w+b') as c:
                    c.write(cert)

            # write json file to disk
            jsons_path = os.path.join(jsons_save_dir, mtjson["Timestamp"]+'.json')
            with open(jsons_path, 'w') as j:
                j.write(decoded_data)
            # Send data to Analyszer
            self.send_to_analyzers(jsons_path)


    def test(self):
        print('Class: ja3-jl')
