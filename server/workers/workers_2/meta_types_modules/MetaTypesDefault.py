#!/usr/bin/env python3

import os
import sys
import time
import json
import redis
import datetime

DEFAULT_FILE_EXTENSION = 'txt'
DEFAULT_FILE_SEPARATOR = b'\n'
ROTATION_SAVE_CYCLE = 5 # seconds
TYPE = 254

class MetaTypesDefault:

    def __init__(self, uuid, json_file):
        self.uuid = uuid
        self.type_name = json_file['type']
        self.save_path = None
        self.parse_json(json_file)

    def test(self):
        print('class: MetaTypesDefault')

    ######## JSON PARSER ########
    def parse_json(self, json_file):
        self.save_file_on_disk = True
        self.file_rotation_mode = True
        self.file_rotation = False
        self.file_separator = b'\n'
        self.filename = b''.join([self.type_name.encode(), b'.txt'])

    ######## PROCESS FUNCTIONS ########
    def process_data(self, data):
        # save data on disk
        if self.is_file_saved_on_disk():
            self.save_data_to_file(data)

    ######## CORE FUNCTIONS ########

    def check_json_file(self, json_file):
        # the json object must contain a type field
        if "type" in json_file:
            return True
        else:
            return False

    # # TODO: update for non rotate_file mode
    def save_json_file(self, json_file):
        self.set_last_time_saved(time.time()) #time_file
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) #date_file
        # update save path
        self.set_save_path( os.path.join(self.get_save_dir(), self.get_filename(file_extention='json')) )
        # save json
        with open(self.get_save_path(), 'w') as f:
            f.write(json.dumps(json_file))
        # update save path for 254 files type
        self.set_save_path( os.path.join(self.get_save_dir(), self.get_filename()) )

    def save_data_to_file(self, data):
        if self.is_file_rotation_mode():
            self.save_rotate_file(data)


    def save_rotate_file(self, data):
        if not self.get_file_rotation():
            new_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            # check if a new file rotation is needed                                        # # TODO: change ROTATION_SAVE_CYCLE
            if ( new_date[0:8] != self.get_last_saved_date()[0:8] ) or ( int(time.time()) - self.get_last_time_saved() > ROTATION_SAVE_CYCLE ):
                self.set_rotate_file(True)

        # rotate file
        if self.get_file_rotation():
            # init save path
            if self.get_save_path() is None:
                self.set_last_time_saved(time.time())
                self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                # update save path
                self.set_save_path( os.path.join(self.get_save_dir(), self.get_filename()) )

            # rotate file
            if self.get_file_separator() in data:
                end_file, start_new_file = data.rsplit(self.get_file_separator(), maxsplit=1)
                # save end of file
                with open(self.get_save_path(), 'ab') as f:
                    f.write(end_file)

                # set last saved date/time
                self.set_last_time_saved(time.time())
                self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                # update save path
                self.set_save_path( os.path.join(self.get_save_dir(), self.get_filename()) )

                # save start of new file
                if start_new_file != b'':
                    with open(self.get_save_path(), 'ab') as f:
                        f.write(start_new_file)
                # end of rotation
                self.set_rotate_file(False)

            # wait file separator
            else:
                with open(self.get_save_path(), 'ab') as f:
                    f.write(data)
        else:
            # save file
            with open(self.get_save_path(), 'ab') as f:
                f.write(data)


    def save_same_directory(self, data):
        pass

    ######## GET FUNCTIONS ########

    def get_type_name(self):
        return self.type_name

    def get_file_separator(self):
        return self.file_separator

    def get_uuid(self):
        return self.uuid

    def get_filename(self, file_extention=None):
        if file_extention is None:
            file_extention = DEFAULT_FILE_EXTENSION
        # File Rotation, : data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation_mode():
            return '{}-{}-{}-{}-{}.{}'.format(self.uuid, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day(), self.get_last_saved_hour_minute(), file_extention)

    def get_save_dir(self):
        # File Rotation, save data in directory: data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation_mode():
            data_directory_uuid_type = os.path.join('../../data', self.get_uuid(), str(TYPE))
            return os.path.join(data_directory_uuid_type, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day() , self.type_name)

        # # TODO: save global type dir ???
        if self.is_file_saved_on_disk():
            pass

    def get_save_path(self):
        return self.save_path

    def is_file_saved_on_disk(self):
        if self.save_file_on_disk:
            return True
        else:
            return False

    def is_file_rotation_mode(self):
        if self.file_rotation_mode:
            return True
        else:
            return False

    def get_file_rotation(self):
        return self.file_rotation

    def get_last_time_saved(self):
        return self.last_time_saved

    def get_last_saved_date(self):
        return self.last_saved_date

    def get_last_saved_year(self):
        return self.last_saved_date[0:4]

    def get_last_saved_month(self):
        return self.last_saved_date[4:6]

    def get_last_saved_day(self):
        return self.last_saved_date[6:8]

    def get_last_saved_hour_minute(self):
        return self.last_saved_date[8:14]

    ######## SET FUNCTIONS ########

    def set_rotate_file(self, boolean_value):
        self.file_rotation = boolean_value

    def set_last_time_saved(self, value_time):
        self.last_time_saved = int(value_time)

    def set_last_saved_date(self, date):
        self.last_saved_date = date

    def set_save_path(self, save_path):
        # # TODO: create directory
        dir_path = os.path.dirname(save_path)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        self.save_path = save_path

##############
