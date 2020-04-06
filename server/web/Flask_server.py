#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import re
import ssl
import sys
import json
import time
import uuid
import flask
import redis
import random
import datetime
import ipaddress

import subprocess

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response, escape
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

import bcrypt

# Import Role_Manager
from Role_Manager import create_user_db, check_password_strength, check_user_role_integrity
from Role_Manager import login_user_basic, login_admin

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib'))
from User import User
import Sensor
import ConfigLoader
import Analyzer_Queue

# Import Blueprint
from blueprints.restApi import restApi
from blueprints.settings import settings
from blueprints.analyzer_queue import analyzer_queue

baseUrl = ''
if baseUrl != '':
    baseUrl = '/'+baseUrl

all_server_modes = ('registration', 'shared-secret')

default_max_entries_by_stream = 10000
analyzer_list_max_default_size = 10000

default_analyzer_max_line_len = 3000

json_type_description_path = os.path.join(os.environ['D4_HOME'], 'web/static/json/type.json')

### Config ###
config_loader = ConfigLoader.ConfigLoader()

# get data directory
use_default_save_directory = config_loader.get_config_boolean("Save_Directories", "use_default_save_directory")
# check if field is None
if use_default_save_directory:
    data_directory = os.path.join(os.environ['D4_HOME'], 'data')
else:
    data_directory = config_loader.get_config_str("Save_Directories", "save_directory")

server_mode = config_loader.get_config_str("D4_Server", "server_mode")
if server_mode not in all_server_modes:
    print('Error: incorrect server_mode')

try:
    FLASK_PORT = config_loader.get_config_int("Flask_Server", "port")
except Exception:
    FLASK_PORT = 7000

redis_server_stream = config_loader.get_redis_conn("Redis_STREAM")
redis_server_metadata = config_loader.get_redis_conn("Redis_METADATA")
redis_users = config_loader.get_redis_conn("Redis_SERV")
redis_server_analyzer = config_loader.get_redis_conn("Redis_ANALYZER")
r_cache = config_loader.get_redis_conn("Redis_CACHE")

config_loader = None
###  ###

with open(json_type_description_path, 'r') as f:
    json_type = json.loads(f.read())
json_type_description = {}
for type_info in json_type:
    json_type_description[type_info['type']] = type_info

Flask_dir = os.path.join(os.environ['D4_HOME'], 'web')

# =========  TLS  =========#
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.load_cert_chain(certfile=os.path.join(Flask_dir, 'server.crt'), keyfile=os.path.join(Flask_dir, 'server.key'))
#print(ssl_context.get_ciphers())
# =========       =========#

app = Flask(__name__, static_url_path=baseUrl+'/static/')
app.config['MAX_CONTENT_LENGTH'] = 900 * 1024 * 1024

# ========= Cookie name ========
app.config.update(SESSION_COOKIE_NAME='d4_project_server{}'.format(uuid.uuid4().int))

# ========= session ========
app.secret_key = str(random.getrandbits(256))
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
# =========       =========#

# =========  BLUEPRINT  =========#
app.register_blueprint(restApi)
app.register_blueprint(settings)
app.register_blueprint(analyzer_queue)
# =========       =========#

# ========= LOGIN MANAGER ========

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
# =========       =========#

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
        if os.path.isdir(uuid_data_directory):
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
    # API - JSON
    if request.path.startswith('/api/'):
        return Response(json.dumps({"status": "error", "reason": "404 Not Found"}, indent=2, sort_keys=True), mimetype='application/json'), 404
    # UI - HTML Template
    else:
        return render_template('404.html'), 404

@app.errorhandler(405)
def _handle_client_error(e):
    if request.path.startswith('/api/'):
        res_dict = {"status": "error", "reason": "Method Not Allowed: The method is not allowed for the requested URL"}
        anchor_id = request.path[8:]
        anchor_id = anchor_id.replace('/', '_')
        api_doc_url = 'https://d4-project.org#{}'.format(anchor_id)
        res_dict['documentation'] = api_doc_url
        return Response(json.dumps(res_dict, indent=2, sort_keys=True), mimetype='application/json'), 405
    else:
        return

# ========== ROUTES ============
@app.route('/login', methods=['POST', 'GET'])
def login():

    current_ip = request.remote_addr
    login_failed_ip = r_cache.get('failed_login_ip:{}'.format(current_ip))

    # brute force by ip
    if login_failed_ip:
        login_failed_ip = int(login_failed_ip)
        if login_failed_ip >= 5:
            error = 'Max Connection Attempts reached, Please wait {}s'.format(r_cache.ttl('failed_login_ip:{}'.format(current_ip)))
            return render_template("login.html", error=error)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        #next_page = request.form.get('next_page')

        if username is not None:
            user = User.get(username)

            login_failed_user_id = r_cache.get('failed_login_user_id:{}'.format(username))
            # brute force by user_id
            if login_failed_user_id:
                login_failed_user_id = int(login_failed_user_id)
                if login_failed_user_id >= 5:
                    error = 'Max Connection Attempts reached, Please wait {}s'.format(r_cache.ttl('failed_login_user_id:{}'.format(username)))
                    return render_template("login.html", error=error)

            if user and user.check_password(password):
                #if not check_user_role_integrity(user.get_id()):
                #    error = 'Incorrect User ACL, Please contact your administrator'
                #    return render_template("login.html", error=error)
                login_user(user) ## TODO: use remember me ?
                if user.request_password_change():
                    return redirect(url_for('change_password'))
                else:
                    return redirect(url_for('index'))
            # login failed
            else:
                # set brute force protection
                #logger.warning("Login failed, ip={}, username={}".format(current_ip, username))
                r_cache.incr('failed_login_ip:{}'.format(current_ip))
                r_cache.expire('failed_login_ip:{}'.format(current_ip), 300)
                r_cache.incr('failed_login_user_id:{}'.format(username))
                r_cache.expire('failed_login_user_id:{}'.format(username), 300)

                error = 'Password Incorrect'
                return render_template("login.html", error=error)

        return 'please provide a valid username'

    else:
        #next_page = request.args.get('next')
        error = request.args.get('error')
        return render_template("login.html" , error=error)

@app.route('/change_password', methods=['POST', 'GET'])
@login_required
def change_password():
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    error = request.args.get('error')

    if error:
        return render_template("change_password.html", error=error)

    if current_user.is_authenticated and password1!=None:
        if password1==password2:
            if check_password_strength(password1):
                user_id = current_user.get_id()
                create_user_db(user_id , password1, update=True)
                return redirect(url_for('index'))
            else:
                error = 'Incorrect password'
                return render_template("change_password.html", error=error)
        else:
            error = "Passwords don't match"
            return render_template("change_password.html", error=error)
    else:
        error = 'Please choose a new password'
        return render_template("change_password.html", error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# role error template
@app.route('/role', methods=['POST', 'GET'])
@login_required
def role():
    return render_template("error/403.html"), 403

@app.route('/')
@login_required
@login_user_basic
def index():
    date = datetime.datetime.now().strftime("%Y/%m/%d")
    return render_template("index.html", date=date)

@app.route('/_json_daily_uuid_stats')
@login_required
@login_user_basic
def _json_daily_uuid_stats():
    date = datetime.datetime.now().strftime("%Y%m%d")
    daily_uuid = redis_server_metadata.zrange('daily_uuid:{}'.format(date), 0, -1, withscores=True)

    data_daily_uuid = []
    for result in daily_uuid:
        data_daily_uuid.append({"key": result[0], "value": int(result[1])})

    return jsonify(data_daily_uuid)

@app.route('/_json_daily_type_stats')
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
def server_management():
    nb_sensors_registered = Sensor.get_nb_registered_sensors()
    nb_sensors_pending = Sensor.get_nb_pending_sensor()

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
        for analyzer_uuid in Analyzer_Queue.get_all_queues_by_type(type):
            list_analyzer_uuid.append(Analyzer_Queue.get_queue_metadata(analyzer_uuid, format_type=type))

        for analyzer_uuid in Analyzer_Queue.get_all_queues_group_by_type(type):
            list_analyzer_uuid.append(Analyzer_Queue.get_queue_metadata(analyzer_uuid, format_type=type, force_is_group_queue=True))

        list_accepted_types.append({"id": int(type), "description": description, 'list_analyzer_uuid': list_analyzer_uuid})

    list_accepted_extended_types = []
    l_queue_extended_type = []
    for extended_type in redis_server_metadata.smembers('server:accepted_extended_type'):
        list_accepted_extended_types.append({"name": extended_type, 'list_analyzer_uuid': []})

        for extended_queue_uuid in Analyzer_Queue.get_all_queues_by_extended_type(extended_type):
            l_queue_extended_type.append(Analyzer_Queue.get_queue_metadata(extended_queue_uuid, format_type=254, extended_type=extended_type))

        for extended_queue_uuid in Analyzer_Queue.get_all_queues_group_by_extended_type(extended_type):
            l_queue_extended_type.append(Analyzer_Queue.get_queue_metadata(extended_queue_uuid, format_type=254, extended_type=extended_type, force_is_group_queue=True))


    return render_template("server_management.html", list_accepted_types=list_accepted_types, list_accepted_extended_types=list_accepted_extended_types,
                            server_mode=server_mode,
                            l_queue_extended_type=l_queue_extended_type,
                            nb_sensors_registered=nb_sensors_registered, nb_sensors_pending=nb_sensors_pending,
                            default_analyzer_max_line_len=default_analyzer_max_line_len,
                            blacklisted_ip=blacklisted_ip, unblacklisted_ip=unblacklisted_ip,
                            blacklisted_uuid=blacklisted_uuid, unblacklisted_uuid=unblacklisted_uuid)

@app.route('/uuid_management')
@login_required
@login_user_basic
def uuid_management():
    uuid_sensor = request.args.get('uuid')
    if is_valid_uuid_v4(uuid_sensor):
        uuid_sensor = uuid_sensor.replace('-', '')

        disk_stats = get_uuid_disk_statistics(uuid_sensor)
        first_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'first_seen')
        if first_seen:
            first_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(first_seen)))
        else:
            first_seen_gmt = '-'
        last_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'last_seen')
        if last_seen:
            last_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_seen)))
        else:
            last_seen_gmt = '-'
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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

@app.route('/server/registered_sensor')
@login_required
@login_admin
def registered_sensor():
    sensors = Sensor.get_registered_sensors()
    all_sensors = []
    for sensor_uuid in sensors:
        all_sensors.append(Sensor._get_sensor_metadata(sensor_uuid, time_format='gmt', sensor_types=True))
    return render_template("registered_sensors.html", all_sensors=all_sensors)

@app.route('/server/pending_sensor')
@login_required
@login_admin
def pending_sensors():
    sensors = Sensor.get_pending_sensor()
    all_pending = []
    for sensor_uuid in sensors:
        all_pending.append(Sensor._get_sensor_metadata(sensor_uuid, first_seen=False, last_seen=False))
    return render_template("pending_sensor.html", all_pending=all_pending)

@app.route('/server/approve_sensor')
@login_required
@login_admin
def approve_sensor():
    uuid_sensor = request.args.get('uuid')
    res = Sensor.approve_sensor({'uuid': uuid_sensor})
    if res[1] == 200:
        return redirect(url_for('pending_sensors'))
    else:
        return jsonify(res[0])

@app.route('/server/delete_pending_sensor')
@login_required
@login_admin
def delete_pending_sensor():
    uuid_sensor = request.args.get('uuid')
    res = Sensor.delete_pending_sensor({'uuid': uuid_sensor})
    if res[1] == 200:
        return redirect(url_for('pending_sensors'))
    else:
        return jsonify(res[0])

@app.route('/server/delete_registered_sensor')
@login_required
@login_admin
def delete_registered_sensor():
    uuid_sensor = request.args.get('uuid')
    res = Sensor.delete_registered_sensor({'uuid': uuid_sensor})
    if res[1] == 200:
        return redirect(url_for('registered_sensor'))
    else:
        return jsonify(res[0])

@app.route('/uuid_change_stream_max_size')
@login_required
@login_user_basic
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
@login_required
@login_user_basic
def uuid_change_description():
    uuid_sensor = request.args.get('uuid')
    description = request.args.get('description')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.hset('metadata_uuid:{}'.format(uuid_sensor), 'description', description)
        return jsonify()
    else:
        return jsonify({'error':'invalid uuid'}), 400

@app.route('/empty_analyzer_queue')
@login_required
@login_user_basic
def empty_analyzer_queue():
    analyzer_uuid = request.args.get('analyzer_uuid')
    format_type = request.args.get('type')
    metatype_name = request.args.get('metatype_name')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(analyzer_uuid):
        if format_type == 254:
            format_type = metatype_name
        Analyzer_Queue.flush_queue(analyzer_uuid, format_type)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/remove_analyzer')
@login_required
@login_user_basic
def remove_analyzer():
    analyzer_uuid = request.args.get('analyzer_uuid')
    format_type = request.args.get('type')
    metatype_name = request.args.get('metatype_name')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(analyzer_uuid):
        Analyzer_Queue.remove_queues(analyzer_uuid, format_type)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/analyzer_change_max_size')
@login_required
@login_user_basic
def analyzer_change_max_size():
    analyzer_uuid = request.args.get('analyzer_uuid')
    user = request.args.get('redirect')
    max_size_analyzer = request.args.get('max_size_analyzer')
    if is_valid_uuid_v4(analyzer_uuid):
        Analyzer_Queue.edit_queue_max_size(analyzer_uuid, max_size_analyzer)
        if user:
            return redirect(url_for('server_management'))
    else:
        return 'Invalid uuid'

@app.route('/kick_uuid')
@login_required
@login_user_basic
def kick_uuid():
    uuid_sensor = request.args.get('uuid')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_stream.sadd('server:sensor_to_kick', uuid_sensor)
        return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/blacklist_uuid')
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
def remove_accepted_extended_type():
    type_name = request.args.get('type_name')
    redis_server_metadata.srem('server:accepted_extended_type', type_name)
    return redirect(url_for('server_management'))

# demo function
@app.route('/delete_data')
@login_required
@login_user_basic
def delete_data():
    date = datetime.datetime.now().strftime("%Y%m%d")
    redis_server_metadata.delete('daily_type:{}'.format(date))
    redis_server_metadata.delete('daily_uuid:{}'.format(date))
    return render_template("index.html")

# demo function
@app.route('/set_uuid_hmac_key')
@login_required
@login_user_basic
def set_uuid_hmac_key():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    key = request.args.get('key')
    hmac_key = escape(key)
    if len(hmac_key)>100:
        hmac_key=hmac_key[:100]
    redis_server_metadata.hset('metadata_uuid:{}'.format(uuid_sensor), 'hmac_key', hmac_key)
    if user:
        return redirect(url_for('uuid_management', uuid=uuid_sensor))


# demo function
@app.route('/whois_data')
@login_required
@login_user_basic
def whois_data():
    ip = request.args.get('ip')
    if is_valid_ip:
        return jsonify(get_whois_ouput(ip))
    else:
        return 'Invalid IP'

@app.route('/generate_uuid')
@login_required
@login_user_basic
def generate_uuid():
    new_uuid = uuid.uuid4()
    return jsonify({'uuid': new_uuid})

@app.route('/get_analyser_sample')
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
@login_required
@login_user_basic
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
    app.run(host='0.0.0.0', port=FLASK_PORT, threaded=True, ssl_context=ssl_context)
