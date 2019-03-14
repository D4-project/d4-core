#!/usr/bin/env python3

import os
import sys
import time
import json
import redis
import datetime
import hashlib
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import pdb

from meta_types_modules.MetaTypesDefault import MetaTypesDefault

class TypeHandler(MetaTypesDefault):

    def __init__(self, uuid, json_file):
        super().__init__(uuid, json_file)
        self.set_rotate_file(True)

    def process_data(self, data):
        self.reconstruct_data(data)
    
    def handle_reconstructed_data(self, data):
        self.set_last_time_saved(time.time())
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        # update save path
        cert_save_dir = os.path.join(self.get_save_dir(), 'certs')
        # Extract certificates from json
        mtjson = json.loads(data)
        for certificate in mtjson["Certificates"]:
#            cert = x509.load_der_x509_certificate(certificate["Raw"].encode(), default_backend())
            m = hashlib.sha256()
            m.update(certificate["Raw"].encode())
            pdb.set_trace()
            certpath = os.path.join(cert_save_dir, m.hexdigest()+'.crt')
            with open(certpath, 'wb') as c:
                c.write(cert)

    def test(self):
        print('Class: ja3-jl')
