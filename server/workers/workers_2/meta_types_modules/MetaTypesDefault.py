#!/usr/bin/env python3

import os
import sys
import time
import json
import gzip
import redis
import shutil
import datetime
import configparser

DEFAULT_FILE_EXTENSION = 'txt'
DEFAULT_FILE_SEPARATOR = b'\n'
ROTATION_SAVE_CYCLE = 300 # seconds
MAX_BUFFER_LENGTH = 100000
TYPE = 254

host_redis_stream = os.getenv('D4_REDIS_STREAM_HOST', "localhost")
port_redis_stream = int(os.getenv('D4_REDIS_STREAM_PORT', 6379))

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0)

host_redis_metadata = os.getenv('D4_REDIS_METADATA_HOST', "localhost")
port_redis_metadata = int(os.getenv('D4_REDIS_METADATA_PORT', 6380))

redis_server_metadata = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=0)

redis_server_analyzer = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=2)

analyzer_list_max_default_size = 10000

class MetaTypesDefault:

    def __init__(self, uuid, json_file):
        self.uuid = uuid
        self.type_name = json_file['type']
        self.save_path = None
        self.buffer = b''
        self.file_rotation_mode = True

        # get file config
        config_file_server = os.path.join(os.environ['D4_HOME'], 'configs/server.conf')
        config_server = configparser.ConfigParser()
        config_server.read(config_file_server)
        # get data directory
        use_default_save_directory = config_server['Save_Directories'].getboolean('use_default_save_directory')
        # check if field is None
        if use_default_save_directory:
            data_directory = os.path.join(os.environ['D4_HOME'], 'data')
        else:
            data_directory = config_server['Save_Directories'].get('save_directory')
        self.data_directory = data_directory

        self.parse_json(json_file)

    def test(self):
        print('class: MetaTypesDefault')

    ######## JSON PARSER ########
    def parse_json(self, json_file):
        self.file_rotation = False
        self.file_separator = b'\n'
        self.filename = b''.join([self.type_name.encode(), b'.txt'])

    ######## PROCESS FUNCTIONS ########
    def process_data(self, data):
        # save data on disk
        self.save_rotate_file(data)

    ######## CORE FUNCTIONS ########

    def check_json_file(self, json_file):
        # the json object must contain a type field
        if "type" in json_file:
            return True
        else:
            return False

    def save_json_file(self, json_file, save_by_uuid=True):
        self.set_last_time_saved(time.time()) #time_file
        self.set_last_saved_date(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) #date_file
        # update save path
        self.set_save_path( os.path.join(self.get_save_dir(save_by_uuid=save_by_uuid), self.get_filename(file_extention='json', save_by_uuid=save_by_uuid)) )
        # save json
        with open(self.get_save_path(), 'w') as f:
            f.write(json.dumps(json_file))
        # update save path for 254 files type
        if self.is_file_rotation_mode():
            self.set_save_path( os.path.join(self.get_save_dir(), self.get_filename()) )


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
                self.compress_file(self.get_save_path())

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
        # no elements
        else:
            # force file_separator when max buffer size is reached
            if self.get_size_buffer() > MAX_BUFFER_LENGTH:
                print('Error, infinite loop, max buffer length reached')
                self.add_to_buffer(self.get_file_separator())

    def handle_reconstructed_data(self, data):
        # send data to analyzer
        self.send_to_analyzers(data)

    def compress_file(self, file_full_path, i=0):
        if i==0:
            compressed_filename = '{}.gz'.format(file_full_path)
        else:
            compressed_filename = '{}.{}.gz'.format(file_full_path, i)
        if os.path.isfile(compressed_filename):
            self.compress_file(file_full_path, i+1)
        else:
            with open(file_full_path, 'rb') as f_in:
                with gzip.open(compressed_filename, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(file_full_path)

    def send_to_analyzers(self, data_to_send):
        ## save full path in anylyzer queue
        for analyzer_uuid in redis_server_metadata.smembers('analyzer:{}:{}'.format(TYPE, self.get_type_name())):
            analyzer_uuid = analyzer_uuid.decode()
            redis_server_analyzer.lpush('analyzer:{}:{}'.format(self.get_type_name(), analyzer_uuid), data_to_send)
            redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'last_updated', time.time())
            analyser_queue_max_size = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
            if analyser_queue_max_size is None:
                analyser_queue_max_size = analyzer_list_max_default_size
            redis_server_analyzer.ltrim('analyzer:{}:{}'.format(self.get_type_name(), analyzer_uuid), 0, analyser_queue_max_size)

    ######## GET FUNCTIONS ########

    def get_type_name(self):
        return self.type_name

    def get_file_separator(self):
        return self.file_separator

    def get_uuid(self):
        return self.uuid

    def get_buffer(self):
        return self.buffer

    def get_size_buffer(self):
        return len(self.buffer)

    def get_filename(self, file_extention=None, save_by_uuid=False):
        if file_extention is None:
            file_extention = DEFAULT_FILE_EXTENSION
        # File Rotation, : data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation_mode() or save_by_uuid:
            return '{}-{}-{}-{}-{}.{}'.format(self.uuid, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day(), self.get_last_saved_hour_minute(), file_extention)

    def get_data_save_directory(self):
        return self.data_directory

    def get_save_dir(self, save_by_uuid=False):
        # File Rotation, save data in directory: data/<uuid>/254/<year>/<month>/<day>/
        if self.is_file_rotation_mode() or save_by_uuid:
            data_directory_uuid_type = os.path.join(self.get_data_save_directory(), self.get_uuid(), str(TYPE))
            return os.path.join(data_directory_uuid_type, self.get_last_saved_year(), self.get_last_saved_month(), self.get_last_saved_day() , self.type_name)

        # data save in the same directory
        else:
            save_dir = os.path.join(self.get_data_save_directory(), 'datas', self.get_type_name())
            if not os.path.isdir(save_dir):
                os.makedirs(save_dir)
            return save_dir

    def get_save_path(self):
        return self.save_path

    def is_empty_buffer(self):
        if self.buffer==b'':
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

    def reset_buffer(self):
        self.buffer = b''

    def set_buffer(self, data):
        self.buffer = data

    def add_to_buffer(self, data):
        self.buffer = b''.join([self.buffer, data])

    def set_rotate_file(self, boolean_value):
        self.file_rotation = boolean_value

    def set_rotate_file_mode(self, boolean_value):
        self.file_rotation_mode = boolean_value

    def set_last_time_saved(self, value_time):
        self.last_time_saved = int(value_time)

    def set_last_saved_date(self, date):
        self.last_saved_date = date

    def set_save_path(self, save_path):
        dir_path = os.path.dirname(save_path)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        self.save_path = save_path
