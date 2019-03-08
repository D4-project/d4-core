#!/usr/bin/env python3

import os
import sys
import time
import json
import redis

DEFAULT_FILE_EXTENSION = 'txt'
DEFAULT_FILE_SEPARATOR = b'\n'
ROTATION_SAVE_CYCLE = 10 # seconds
TYPE = 254

class MetaTypesDefault:

    def __init__(self, uuid, json_file):
        self.session_uuid = uuid
        self.type_name = json_file['type']
        self.parse_json(json_file)
        print('end default init')

    def test(self):
        print(self.session_uuid)

    ######## JSON PARSER ########
    def parse_json(self, uuid, json_file):
        self.uuid = uuid
        self.save_file_on_disk = True
        self.is_file_rotation = True
        self.file_separator = b'\n'
        self.filename = b'{}.txt'.format(self.type_name)

    ######## PROCESS FUNCTIONS ########
    def process_data(self, data):
        # save data on disk
        if self.is_file_saved_on_disk():
            self.save_data_to_file(data)

        print('end process_data')

    ######## CORE FUNCTIONS ########

    def check_json_file(self, json_file):
        # the json object must contain a type field
        if "type" in json_file:
            return True
        else:
            return False

    def save_json_file(self, json_file):
        self.last_time_saved = time.time() #time_file
        self.last_saved_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S") #date_file

        save_path = os.path.join(self.get_save_dir(file_extention='json'), self.get_save_dir())
        with open(save_path, 'w') as f:
            f.write(json.dumps(full_json))

    def save_data_to_file(self, data):
        if self.is_file_rotation():
            self.save_rotate_file(data)


    def save_rotate_file(self, data):
        new_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # check if a new file rotation is needed                                        # # TODO: change ROTATION_SAVE_CYCLE
        if ( new_date[0:8] != self.get_last_time_saved()[0:8] ) or ( time.time() - self.get_last_time_saved > ROTATION_SAVE_CYCLE ):
            date_file = new_date
            self.set_last_saved_date(new_date)
            self.set_rotate_file(True)
            

    def save_same_directory(self, data):
        pass

    ######## GET FUNCTIONS ########

    def get_type_name(self):
        return self.type_name

    def get_file_separator(self):
        return self.file_separator

    def get_filename(self, file_extention=None):
        if file_extention is None:
            file_extention = DEFAULT_FILE_EXTENSION
        # File Rotation, : data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation():
            return '{}-{}-{}-{}-{}.{}'.format(self.uuid, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day(), self.get_last_saved_hour_minute(), file_extention)

    # todo save save_dir ???
    def get_save_dir(self):
        # File Rotation, save data in directory: data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation():
            data_directory_uuid_type = os.path.join('../../data', self.uuid, str(TYPE))
            return os.path.join(data_directory_uuid_type, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day() , self.type_name)

        # # TODO: save global type dir ???
        if self.is_file_saved_on_disk():
            pass

    def is_file_saved_on_disk(self):
        return self.save_file_on_disk

    def is_file_rotation(self):
        return self.is_file_rotation

    def get_last_time_saved(self):
        return self.last_time_saved

    def get_last_saved_date(self):
        return self.last_saved_date

    def get_last_saved_year(self):
        return self.last_saved_date[0:4]

    def get_last_saved_month(self):
        return self.last_saved_date[4:6]

    def get_last_saved_year(self):
        return self.last_saved_date[6:8]

    def get_last_saved_hour_minute(self):
        return self.last_saved_date[8:14]

    ######## SET FUNCTIONS ########

    def set_rotate_file(self, boolean_value):
        self.file_rotation = boolean_value

    def set_last_saved_date(self, date):
        self.get_last_saved_date = date

##############
