#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import re
import sys
import uuid
import time
import json
import redis
import flask
import datetime
import ipaddress
import configparser

import subprocess

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for

baseUrl = ''
if baseUrl != '':
    baseUrl = '/'+baseUrl

host_redis_stream = "localhost"
port_redis_stream = 6379

default_max_entries_by_stream = 10000
analyzer_list_max_default_size = 10000

default_analyzer_max_line_len = 3000

json_type_description_path = os.path.join(os.environ['D4_HOME'], 'web/static/json/type.json')

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

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0,
                    decode_responses=True)

host_redis_metadata = "localhost"
port_redis_metadata= 6380

redis_server_metadata = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=0,
                    decode_responses=True)

redis_server_analyzer = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=2,
                    decode_responses=True)

with open(json_type_description_path, 'r') as f:
    json_type = json.loads(f.read())
json_type_description = {}
for type_info in json_type:
    json_type_description[type_info['type']] = type_info

app = Flask(__name__, static_url_path=baseUrl+'/static/')
app.config['MAX_CONTENT_LENGTH'] = 900 * 1024 * 1024

# ========== FUNCTIONS ============
def is_valid_uuid_v4(header_uuid):
    try:
        header_uuid=header_uuid.replace('-', '')
        uuid_test = uuid.UUID(hex=header_uuid, version=4)
        return uuid_test.hex == header_uuid
    except:
        return False

def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def is_valid_network(ip_network):
    try:
        ipaddress.ip_network(ip_network)
        return True
    except ValueError:
        return False

# server_management input handler
def get_server_management_input_handler_value(value):
    if value is not None:
        if value !="0":
            try:
                value=int(value)
            except:
                value=0
        else:
            value=0
    return value

def get_json_type_description():
    return json_type_description

def get_whois_ouput(ip):
    if is_valid_ip(ip):
        process = subprocess.run(["whois", ip], stdout=subprocess.PIPE)
        return re.sub(r"#.*\n?", '', process.stdout.decode()).lstrip('\n').rstrip('\n')
    else:
        return ''

def get_substract_date_range(num_day, date_from=None):
    if date_from is None:
        date_from = datetime.datetime.now()
    else:
        date_from = datetime.date(int(date_from[0:4]), int(date_from[4:6]), int(date_from[6:8]))

    l_date = []
    for i in range(num_day):
        date = date_from - datetime.timedelta(days=i)
        l_date.append( date.strftime('%Y%m%d') )
    return list(reversed(l_date))

def get_uuid_all_types_disk(uuid_name):
    uuid_data_directory = os.path.join(data_directory, uuid_name)
    all_types_on_disk = []
    # Get all types save on disk
    for file in os.listdir(uuid_data_directory):
        uuid_type_path = os.path.join(uuid_data_directory, file)
        if os.path.isdir(uuid_type_path):
            all_types_on_disk.append(file)
    return all_types_on_disk

def get_uuid_disk_statistics(uuid_name, date_day='', type='', all_types_on_disk=[], all_stats=True):
    # # TODO: escape uuid_name

    stat_disk_uuid = {}
    uuid_data_directory = os.path.join(data_directory, uuid_name)
    if date_day:
        directory_date = os.path.join(date_day[0:4], date_day[4:6], date_day[6:8])
    all_types_on_disk = {}

    if all_types_on_disk:
        for type in all_types_on_disk:
            if date_day:
                uuid_type_path = os.path.join(uuid_data_directory, type, directory_date)
            else:
                uuid_type_path = os.path.join(uuid_data_directory, type)
            all_types_on_disk[type] = uuid_type_path
    else:
        # Get all types save on disk
        for file in os.listdir(uuid_data_directory):
            if date_day:
                uuid_type_path = os.path.join(uuid_data_directory, file, directory_date)
            else:
                uuid_type_path = os.path.join(uuid_data_directory, file)
            if os.path.isdir(uuid_type_path):
                all_types_on_disk[file] = uuid_type_path

    nb_file = 0
    total_size = 0

    for uuid_type in all_types_on_disk:
        nb_file_type = 0
        total_size_type = 0
        for dirpath, dirnames, filenames in os.walk(all_types_on_disk[uuid_type]):
            stat_disk_uuid[uuid_type] = {}
            for f in filenames:
                fp = os.path.join(dirpath, f)
                file_size = os.path.getsize(fp)
                total_size_type += file_size
                total_size += file_size
                nb_file_type += 1
                nb_file += 1
            stat_disk_uuid[uuid_type]['nb_files'] = nb_file_type
            stat_disk_uuid[uuid_type]['total_size'] = total_size_type
    if all_stats:
        stat_all = {}
        stat_all['nb_files'] = nb_file
        stat_all['total_size'] = total_size
        stat_disk_uuid['All'] = stat_all
    return stat_disk_uuid

# ========== ERRORS ============

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# ========== ROUTES ============
@app.route('/test')
def test():
    return 'test'

@app.route('/')
def index():
    date = datetime.datetime.now().strftime("%Y/%m/%d")
    return render_template("index.html", date=date)

@app.route('/_json_daily_uuid_stats')
def _json_daily_uuid_stats():
    date = datetime.datetime.now().strftime("%Y%m%d")
    daily_uuid = redis_server_metadata.zrange('daily_uuid:{}'.format(date), 0, -1, withscores=True)

    data_daily_uuid = []
    for result in daily_uuid:
        data_daily_uuid.append({"key": result[0], "value": int(result[1])})

    return jsonify(data_daily_uuid)

@app.route('/_json_daily_type_stats')
def _json_daily_type_stats():
    date = datetime.datetime.now().strftime("%Y%m%d")
    daily_uuid = redis_server_metadata.zrange('daily_type:{}'.format(date), 0, -1, withscores=True)
    json_type_description = get_json_type_description()

    data_daily_uuid = []
    for result in daily_uuid:
        try:
            type_description = json_type_description[int(result[0])]['description']
        except:
            type_description = 'Please update your web server'
        data_daily_uuid.append({"key": '{}: {}'.format(result[0], type_description), "value": int(result[1])})

    return jsonify(data_daily_uuid)

@app.route('/sensors_status')
def sensors_status():
    active_connection_filter = request.args.get('active_connection_filter')
    if active_connection_filter is None:
        active_connection_filter = False
    else:
        if active_connection_filter=='True':
            active_connection_filter = True
        else:
            active_connection_filter = False

    date = datetime.datetime.now().strftime("%Y%m%d")

    if not active_connection_filter:
        daily_uuid = redis_server_metadata.zrange('daily_uuid:{}'.format(date), 0, -1)
    else:
        daily_uuid = redis_server_stream.smembers('active_connection')

    type_description_json = get_json_type_description()

    status_daily_uuid = []
    types_description = {}
    for result in daily_uuid:
        first_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'first_seen')
        first_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(first_seen)))
        last_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'last_seen')
        last_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_seen)))
        description = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'description')
        if not description:
            description = ''
        type_connection_status = {}
        l_uuid_types = []
        l_uuid_typ = redis_server_metadata.smembers('all_types_by_uuid:{}'.format(result))
        for type in l_uuid_typ:
            type = int(type)
            if redis_server_stream.sismember('active_connection:{}'.format(type), result):
                type_connection_status[type] = True
            else:
                type_connection_status[type] = False
            l_uuid_types.append(type)
            if type not in types_description:
                types_description[type] = type_description_json[type]['description']
                if not types_description[type]:
                    types_description[type] = 'please update your web server'

        l_uuid_types.sort()
        if 254 in l_uuid_types:
            extended_type = list(redis_server_metadata.smembers('all_extended_types_by_uuid:{}'.format(result)))
            extended_type.sort()
            for extended in extended_type:
                if redis_server_stream.sismember('active_connection_extended_type:{}'.format(result), extended):
                    type_connection_status[extended] = True
                else:
                    type_connection_status[extended] = False
                types_description[extended] = ''
            l_uuid_types.extend(extended_type)
        if redis_server_metadata.sismember('blacklist_ip_by_uuid', result):
            Error = "All IP using this UUID are Blacklisted"
        elif redis_server_metadata.sismember('blacklist_uuid', result):
            Error = "Blacklisted UUID"
        else:
            Error = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'Error')
        if redis_server_stream.sismember('active_connection', result):
            active_connection = True
        else:
            active_connection = False

        if first_seen is not None and last_seen is not None:
            status_daily_uuid.append({"uuid": result,
                                        "active_connection": active_connection,
                                        "type_connection_status": type_connection_status,
                                        "description": description,
                                        "first_seen_gmt": first_seen_gmt, "last_seen_gmt": last_seen_gmt,
                                        "l_uuid_types": l_uuid_types, "Error": Error})

    return render_template("sensors_status.html", status_daily_uuid=status_daily_uuid,
                                types_description=types_description,
                                active_connection_filter=active_connection_filter)

@app.route('/show_active_uuid')
def show_active_uuid():
    #swap switch value
    active_connection_filter = request.args.get('show_active_connection')
    if active_connection_filter is None:
        active_connection_filter = True
    else:
        if active_connection_filter=='True':
            active_connection_filter = False
        else:
            active_connection_filter = True

    return redirect(url_for('sensors_status', active_connection_filter=active_connection_filter))

@app.route('/server_management')
def server_management():
    blacklisted_ip = request.args.get('blacklisted_ip')
    unblacklisted_ip = request.args.get('unblacklisted_ip')
    blacklisted_uuid = request.args.get('blacklisted_uuid')
    unblacklisted_uuid = request.args.get('unblacklisted_uuid')

    blacklisted_ip = get_server_management_input_handler_value(blacklisted_ip)
    unblacklisted_ip = get_server_management_input_handler_value(unblacklisted_ip)
    blacklisted_uuid = get_server_management_input_handler_value(blacklisted_uuid)
    unblacklisted_uuid = get_server_management_input_handler_value(unblacklisted_uuid)

    json_type_description = get_json_type_description()

    list_accepted_types = []
    list_analyzer_types = []
    for type in redis_server_metadata.smembers('server:accepted_type'):
        try:
            description = json_type_description[int(type)]['description']
        except:
            description = 'Please update your web server'

        list_analyzer_uuid = []
        for analyzer_uuid in redis_server_metadata.smembers('analyzer:{}'.format(type)):
            size_limit = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
            if size_limit is None:
                size_limit = analyzer_list_max_default_size
            last_updated = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'last_updated')
            if last_updated is None:
                last_updated = 'Never'
            else:
                last_updated = datetime.datetime.fromtimestamp(float(last_updated)).strftime('%Y-%m-%d %H:%M:%S')
            description_analyzer = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'description')
            if description_analyzer is None:
                description_analyzer = ''
            len_queue = redis_server_analyzer.llen('analyzer:{}:{}'.format(type, analyzer_uuid))
            if len_queue is None:
                len_queue = 0
            list_analyzer_uuid.append({'uuid': analyzer_uuid, 'description': description_analyzer, 'size_limit': size_limit,'last_updated': last_updated, 'length': len_queue})

        list_accepted_types.append({"id": int(type), "description": description, 'list_analyzer_uuid': list_analyzer_uuid})

    list_accepted_extended_types = []
    for extended_type in redis_server_metadata.smembers('server:accepted_extended_type'):

        list_analyzer_uuid = []
        for analyzer_uuid in redis_server_metadata.smembers('analyzer:254:{}'.format(extended_type)):
            size_limit = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'max_size')
            if size_limit is None:
                size_limit = analyzer_list_max_default_size
            last_updated = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'last_updated')
            if last_updated is None:
                last_updated = 'Never'
            else:
                last_updated = datetime.datetime.fromtimestamp(float(last_updated)).strftime('%Y-%m-%d %H:%M:%S')
            description_analyzer = redis_server_metadata.hget('analyzer:{}'.format(analyzer_uuid), 'description')
            if description_analyzer is None:
                description_analyzer = ''
            len_queue = redis_server_analyzer.llen('analyzer:{}:{}'.format(extended_type, analyzer_uuid))
            if len_queue is None:
                len_queue = 0
            list_analyzer_uuid.append({'uuid': analyzer_uuid, 'description': description_analyzer, 'size_limit': size_limit,'last_updated': last_updated, 'length': len_queue})

        list_accepted_extended_types.append({"name": extended_type, 'list_analyzer_uuid': list_analyzer_uuid})

    return render_template("server_management.html", list_accepted_types=list_accepted_types, list_accepted_extended_types=list_accepted_extended_types,
                            default_analyzer_max_line_len=default_analyzer_max_line_len,
                            blacklisted_ip=blacklisted_ip, unblacklisted_ip=unblacklisted_ip,
                            blacklisted_uuid=blacklisted_uuid, unblacklisted_uuid=unblacklisted_uuid)

@app.route('/uuid_management')
def uuid_management():
    uuid_sensor = request.args.get('uuid')
    if is_valid_uuid_v4(uuid_sensor):

        disk_stats = get_uuid_disk_statistics(uuid_sensor)
        first_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'first_seen')
        first_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(first_seen)))
        last_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'last_seen')
        last_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_seen)))
        description = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'description')
        if not description:
            description = ''
        Error = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'Error')
        if redis_server_stream.exists('temp_blacklist_uuid:{}'.format(uuid_sensor)):
            temp_blacklist_uuid = True
        else:
            temp_blacklist_uuid = False
        if redis_server_metadata.sismember('blacklist_uuid', uuid_sensor):
            blacklisted_uuid = True
            Error = "Blacklisted UUID"
        else:
            blacklisted_uuid = False
        if redis_server_metadata.sismember('blacklist_ip_by_uuid', uuid_sensor):
            blacklisted_ip_by_uuid = True
            Error = "All IP using this UUID are Blacklisted"
        else:
            blacklisted_ip_by_uuid = False
        data_uuid= {"description": description,
                    "temp_blacklist_uuid": temp_blacklist_uuid,
                    "blacklisted_uuid": blacklisted_uuid, "blacklisted_ip_by_uuid": blacklisted_ip_by_uuid,
                    "first_seen_gmt": first_seen_gmt, "last_seen_gmt": last_seen_gmt, "Error": Error}

        if redis_server_stream.sismember('active_connection', uuid_sensor):
            active_connection = True
        else:
            active_connection = False

        max_uuid_stream = redis_server_metadata.hget('stream_max_size_by_uuid', uuid_sensor)
        if max_uuid_stream is not None:
            max_uuid_stream = int(max_uuid_stream)
        else:
            max_uuid_stream = default_max_entries_by_stream

        uuid_key = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'hmac_key')
        if uuid_key is None:
            uuid_key = redis_server_metadata.get('server:hmac_default_key')

        uuid_all_type_list = []
        uuid_all_type = redis_server_metadata.smembers('all_types_by_uuid:{}'.format(uuid_sensor))
        for type in uuid_all_type:
            type_first_seen = redis_server_metadata.hget('metadata_type_by_uuid:{}:{}'.format(uuid_sensor, type), 'first_seen')
            type_last_seen = redis_server_metadata.hget('metadata_type_by_uuid:{}:{}'.format(uuid_sensor, type), 'last_seen')
            if type_first_seen:
                type_first_seen = datetime.datetime.fromtimestamp(float(type_first_seen)).strftime('%Y-%m-%d %H:%M:%S')
            if type_last_seen:
                type_last_seen = datetime.datetime.fromtimestamp(float(type_last_seen)).strftime('%Y-%m-%d %H:%M:%S')
            uuid_all_type_list.append({'type': type, 'first_seen':type_first_seen, 'last_seen': type_last_seen})

        list_ip = redis_server_metadata.lrange('list_uuid_ip:{}'.format(uuid_sensor), 0, -1)
        all_ip = []
        for elem in list_ip:
            ip, d_time = elem.split('-')
            all_ip.append({'ip': ip,'datetime': '{}/{}/{} - {}:{}.{}'.format(d_time[0:4], d_time[5:6], d_time[6:8], d_time[8:10], d_time[10:12], d_time[12:14])})

        return render_template("uuid_management.html", uuid_sensor=uuid_sensor, active_connection=active_connection,
                                uuid_key=uuid_key, data_uuid=data_uuid, uuid_all_type=uuid_all_type_list,
                                disk_stats=disk_stats,
                                max_uuid_stream=max_uuid_stream, all_ip=all_ip)
    else:
        return 'Invalid uuid'

@app.route('/blacklisted_ip')
def blacklisted_ip():
    blacklisted_ip = request.args.get('blacklisted_ip')
    unblacklisted_ip = request.args.get('unblacklisted_ip')
    try:
        page = int(request.args.get('page'))
    except:
        page = 1
    if page <= 0:
        page = 1
    nb_page_max = redis_server_metadata.scard('blacklist_ip')/(1000*2)
    if isinstance(nb_page_max, float):
        nb_page_max = int(nb_page_max)+1
    if page > nb_page_max:
        page = nb_page_max
    start = 1000*(page -1)
    stop = 1000*page

    list_blacklisted_ip = list(redis_server_metadata.smembers('blacklist_ip'))
    list_blacklisted_ip_1 = list_blacklisted_ip[start:stop]
    list_blacklisted_ip_2 = list_blacklisted_ip[stop:stop+1000]
    return render_template("blacklisted_ip.html", list_blacklisted_ip_1=list_blacklisted_ip_1, list_blacklisted_ip_2=list_blacklisted_ip_2,
                            page=page, nb_page_max=nb_page_max,
                            unblacklisted_ip=unblacklisted_ip, blacklisted_ip=blacklisted_ip)

@app.route('/blacklisted_uuid')
def blacklisted_uuid():
    blacklisted_uuid = request.args.get('blacklisted_uuid')
    unblacklisted_uuid = request.args.get('unblacklisted_uuid')
    try:
        page = int(request.args.get('page'))
    except:
        page = 1
    if page <= 0:
        page = 1
    nb_page_max = redis_server_metadata.scard('blacklist_uuid')/(1000*2)
    if isinstance(nb_page_max, float):
        nb_page_max = int(nb_page_max)+1
    if page > nb_page_max:
        page = nb_page_max
    start = 1000*(page -1)
    stop = 1000*page

    list_blacklisted_uuid = list(redis_server_metadata.smembers('blacklist_uuid'))
    list_blacklisted_uuid_1 = list_blacklisted_uuid[start:stop]
    list_blacklisted_uuid_2 = list_blacklisted_uuid[stop:stop+1000]
    return render_template("blacklisted_uuid.html", list_blacklisted_uuid_1=list_blacklisted_uuid_1, list_blacklisted_uuid_2=list_blacklisted_uuid_2,
                            page=page, nb_page_max=nb_page_max,
                            unblacklisted_uuid=unblacklisted_uuid, blacklisted_uuid=blacklisted_uuid)


@app.route('/uuid_change_stream_max_size')
def uuid_change_stream_max_size():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    max_uuid_stream = request.args.get('max_uuid_stream')
    if is_valid_uuid_v4(uuid_sensor):
        try:
            max_uuid_stream = int(max_uuid_stream)
            if max_uuid_stream < 0:
                return 'stream max size, Invalid Integer'
        except:
            return 'stream max size, Invalid Integer'
        redis_server_metadata.hset('stream_max_size_by_uuid', uuid_sensor, max_uuid_stream)
        if user:
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/uuid_change_description')
def uuid_change_description():
    uuid_sensor = request.args.get('uuid')
    description = request.args.get('description')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.hset('metadata_uuid:{}'.format(uuid_sensor), 'description', description)
        return jsonify()
    else:
        return jsonify({'error':'invalid uuid'}), 400

# # TODO: check analyser uuid dont exist
@app.route('/add_new_analyzer')
def add_new_analyzer():
    type = request.args.get('type')
    user = request.args.get('redirect')
    metatype_name = request.args.get('metatype_name')
    analyzer_description = request.args.get('analyzer_description')
    analyzer_uuid = request.args.get('analyzer_uuid')
    if is_valid_uuid_v4(analyzer_uuid):
        try:
            type = int(type)
            if type < 0:
                return 'type, Invalid Integer'
        except:
            return 'type, Invalid Integer'
        if type == 254:
            # # TODO: check metatype_name
            redis_server_metadata.sadd('analyzer:{}:{}'.format(type, metatype_name), analyzer_uuid)
        else:
            redis_server_metadata.sadd('analyzer:{}'.format(type), analyzer_uuid)
        if redis_server_metadata.exists('analyzer:{}:{}'.format(type, metatype_name)) or redis_server_metadata.exists('analyzer:{}'.format(type)):
            redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'description', analyzer_description)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/empty_analyzer_queue')
def empty_analyzer_queue():
    analyzer_uuid = request.args.get('analyzer_uuid')
    type = request.args.get('type')
    metatype_name = request.args.get('metatype_name')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(analyzer_uuid):
        try:
            type = int(type)
            if type < 0:
                return 'type, Invalid Integer'
        except:
            return 'type, Invalid Integer'
        if type == 254:
            redis_server_analyzer.delete('analyzer:{}:{}'.format(metatype_name, analyzer_uuid))
        else:
            redis_server_analyzer.delete('analyzer:{}:{}'.format(type, analyzer_uuid))
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/remove_analyzer')
def remove_analyzer():
    analyzer_uuid = request.args.get('analyzer_uuid')
    type = request.args.get('type')
    metatype_name = request.args.get('metatype_name')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(analyzer_uuid):
        try:
            type = int(type)
            if type < 0:
                return 'type, Invalid Integer'
        except:
            return 'type, Invalid Integer'
        if type == 254:
            redis_server_metadata.srem('analyzer:{}:{}'.format(type, metatype_name), analyzer_uuid)
            redis_server_analyzer.delete('analyzer:{}:{}'.format(metatype_name, analyzer_uuid))
        else:
            redis_server_metadata.srem('analyzer:{}'.format(type), analyzer_uuid)
            redis_server_analyzer.delete('analyzer:{}:{}'.format(type, analyzer_uuid))
        redis_server_metadata.delete('analyzer:{}'.format(analyzer_uuid))
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/analyzer_change_max_size')
def analyzer_change_max_size():
    analyzer_uuid = request.args.get('analyzer_uuid')
    user = request.args.get('redirect')
    max_size_analyzer = request.args.get('max_size_analyzer')
    if is_valid_uuid_v4(analyzer_uuid):
        try:
            max_size_analyzer = int(max_size_analyzer)
            if max_size_analyzer < 0:
                return 'analyzer max size, Invalid Integer'
        except:
            return 'analyzer max size, Invalid Integer'
        redis_server_metadata.hset('analyzer:{}'.format(analyzer_uuid), 'max_size', max_size_analyzer)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/kick_uuid')
def kick_uuid():
    uuid_sensor = request.args.get('uuid')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_stream.sadd('server:sensor_to_kick', uuid_sensor)
        return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/blacklist_uuid')
def blacklist_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(uuid_sensor):
        res = redis_server_metadata.sadd('blacklist_uuid', uuid_sensor)
        if user=="0":
            if res==0:
                return redirect(url_for('server_management', blacklisted_uuid=2))
            else:
                return redirect(url_for('server_management', blacklisted_uuid=1))
        elif user=="1":
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
        else:
            return "404"
    else:
        if user=="0":
            return redirect(url_for('server_management', blacklisted_uuid=0))
        return 'Invalid uuid'

@app.route('/unblacklist_uuid')
def unblacklist_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    page = request.args.get('page')
    if is_valid_uuid_v4(uuid_sensor):
        res = redis_server_metadata.srem('blacklist_uuid', uuid_sensor)
        if page:
            return redirect(url_for('blacklisted_uuid', page=page))
        if user=="0":
            if res==0:
                return redirect(url_for('server_management', unblacklisted_uuid=2))
            else:
                return redirect(url_for('server_management', unblacklisted_uuid=1))
        elif user=="1":
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
        else:
            return "404"
    else:
        if user=="0":
            return redirect(url_for('server_management', unblacklisted_uuid=0))
        return 'Invalid uuid'

@app.route('/blacklist_ip')
def blacklist_ip():
    ip = request.args.get('ip')
    user = request.args.get('redirect')

    if is_valid_ip(ip):
        res = redis_server_metadata.sadd('blacklist_ip', ip)
        if user:
            if res==0:
                return redirect(url_for('server_management', blacklisted_ip=2))
            else:
                return redirect(url_for('server_management', blacklisted_ip=1))
    elif is_valid_network(ip):
        for addr in ipaddress.ip_network(ip):
            res = redis_server_metadata.sadd('blacklist_ip', str(addr))
        if user:
            if res==0:
                return redirect(url_for('server_management', blacklisted_ip=2))
            else:
                return redirect(url_for('server_management', blacklisted_ip=1))
    else:
        if user:
            return redirect(url_for('server_management', blacklisted_ip=0))
        return 'Invalid ip'

@app.route('/unblacklist_ip')
def unblacklist_ip():
    ip = request.args.get('ip')
    user = request.args.get('redirect')
    page = request.args.get('page')
    if is_valid_ip(ip):
        res = redis_server_metadata.srem('blacklist_ip', ip)
        if page:
            return redirect(url_for('blacklisted_ip', page=page))
        if user:
            if res==0:
                return redirect(url_for('server_management', unblacklisted_ip=2))
            else:
                return redirect(url_for('server_management', unblacklisted_ip=1))
    elif is_valid_network(ip):
        for addr in ipaddress.ip_network(ip):
            res = redis_server_metadata.srem('blacklist_ip', str(addr))
        if user:
            if res==0:
                return redirect(url_for('server_management', unblacklisted_ip=2))
            else:
                return redirect(url_for('server_management', unblacklisted_ip=1))
    else:
        if user:
            return redirect(url_for('server_management', unblacklisted_ip=0))
        return 'Invalid ip'

@app.route('/blacklist_ip_by_uuid')
def blacklist_ip_by_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.sadd('blacklist_ip_by_uuid', uuid_sensor)
        if user:
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/unblacklist_ip_by_uuid')
def unblacklist_ip_by_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.srem('blacklist_ip_by_uuid', uuid_sensor)
        if user:
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/add_accepted_type')
def add_accepted_type():
    type = request.args.get('type')
    extended_type_name = request.args.get('extended_type_name')
    user = request.args.get('redirect')
    json_type_description = get_json_type_description()
    try:
        type = int(type)
    except:
        return 'Invalid type'
    if json_type_description[int(type)]:
        redis_server_metadata.sadd('server:accepted_type', type)
        if type == 254:
            redis_server_metadata.sadd('server:accepted_extended_type', extended_type_name)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid type'

@app.route('/remove_accepted_type')
def remove_accepted_type():
    type = request.args.get('type')
    user = request.args.get('redirect')
    json_type_description = get_json_type_description()
    if json_type_description[int(type)]:
        redis_server_metadata.srem('server:accepted_type', type)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid type'

@app.route('/remove_accepted_extended_type')
def remove_accepted_extended_type():
    type_name = request.args.get('type_name')
    redis_server_metadata.srem('server:accepted_extended_type', type_name)
    return redirect(url_for('server_management'))

# demo function
@app.route('/delete_data')
def delete_data():
    date = datetime.datetime.now().strftime("%Y%m%d")
    redis_server_metadata.delete('daily_type:{}'.format(date))
    redis_server_metadata.delete('daily_uuid:{}'.format(date))
    return render_template("index.html")

# demo function
@app.route('/set_uuid_hmac_key')
def set_uuid_hmac_key():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    key = request.args.get('key')
    redis_server_metadata.hset('metadata_uuid:{}'.format(uuid_sensor), 'hmac_key', key)
    if user:
        return redirect(url_for('uuid_management', uuid=uuid_sensor))


# demo function
@app.route('/whois_data')
def whois_data():
    ip = request.args.get('ip')
    if is_valid_ip:
        return jsonify(get_whois_ouput(ip))
    else:
        return 'Invalid IP'

@app.route('/generate_uuid')
def generate_uuid():
    new_uuid = uuid.uuid4()
    return jsonify({'uuid': new_uuid})

@app.route('/get_analyser_sample')
def get_analyser_sample():
    type = request.args.get('type')
    analyzer_uuid = request.args.get('analyzer_uuid')
    max_line_len = request.args.get('max_line_len')
    # get max_line_len
    if max_line_len is not None and max_line_len!= 'undefined':
        try:
            max_line_len = int(max_line_len)
        except:
            max_line_len = default_analyzer_max_line_len
        if max_line_len < 1:
            max_line_len = default_analyzer_max_line_len
    else:
        max_line_len = default_analyzer_max_line_len
    if is_valid_uuid_v4(analyzer_uuid):
        list_queue = redis_server_analyzer.lrange('analyzer:{}:{}'.format(type, analyzer_uuid), 0 ,10)
        list_queue_res = []
        for res in list_queue:
            #limit line len
            if len(res) > max_line_len:
                res = '{} [...]'.format(res[:max_line_len])
            list_queue_res.append('{}\n'.format(res))
        return jsonify(''.join(list_queue_res))
    else:
        return jsonify('Incorrect UUID')

@app.route('/get_uuid_type_history_json')
def get_uuid_type_history_json():
    uuid_sensor = request.args.get('uuid_sensor')
    if is_valid_uuid_v4(uuid_sensor):
        num_day_type = 7
        date_range = get_substract_date_range(num_day_type)
        type_history = []
        range_decoder = []
        all_type = set()
        for date in date_range:
            type_day = redis_server_metadata.zrange('stat_uuid_type:{}:{}'.format(date, uuid_sensor), 0, -1, withscores=True)
            for type in type_day:
                all_type.add(type[0])
            range_decoder.append((date, type_day))

        default_dict_type = {}
        for type in all_type:
            default_dict_type[type] = 0
        for row in range_decoder:
            day_type = default_dict_type.copy()
            date = row[0]
            day_type['date']= date[0:4] + '-' + date[4:6] + '-' + date[6:8]
            for type in row[1]:
                day_type[type[0]]= type[1]
            type_history.append(day_type)

        return jsonify(type_history)
    else:
        return jsonify('Incorrect UUID')

@app.route('/get_uuid_stats_history_json')
def get_uuid_stats_history_json():
    uuid_sensor = request.args.get('uuid_sensor')
    stats = request.args.get('stats')
    if is_valid_uuid_v4(uuid_sensor):
        if stats not in ['nb_files', 'total_size']:
            stats = 'nb_files'

        num_day_type = 7
        date_range = get_substract_date_range(num_day_type)
        stat_type_history = []
        range_decoder = []
        all_type = get_uuid_all_types_disk(uuid_sensor)

        default_dict_type = {}
        for type in all_type:
            default_dict_type[type] = 0

        for date in date_range:
            day_type = default_dict_type.copy()
            daily_stat = get_uuid_disk_statistics(uuid_sensor, date, all_types_on_disk=all_type, all_stats=False)
            day_type['date']= date[0:4] + '-' + date[4:6] + '-' + date[6:8]
            for type_key in daily_stat:
                day_type[type_key] += daily_stat[type_key][stats]
            stat_type_history.append(day_type)

        return jsonify(stat_type_history)
    else:
        return jsonify('Incorrect UUID')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, threaded=True)
