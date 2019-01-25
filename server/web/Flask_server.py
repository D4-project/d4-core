#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import uuid
import time
import json
import redis
import flask
import datetime
import ipaddress

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for

baseUrl = ''
if baseUrl != '':
    baseUrl = '/'+baseUrl

host_redis_stream = "localhost"
port_redis_stream = 6379

default_max_entries_by_stream = 10000

json_type_description_path = os.path.join(os.environ['D4_HOME'], 'web/static/json/type.json')

redis_server_stream = redis.StrictRedis(
                    host=host_redis_stream,
                    port=port_redis_stream,
                    db=0)

host_redis_metadata = "localhost"
port_redis_metadata= 6380

redis_server_metadata = redis.StrictRedis(
                    host=host_redis_metadata,
                    port=port_redis_metadata,
                    db=0,
                    decode_responses=True)

app = Flask(__name__, static_url_path=baseUrl+'/static/')
app.config['MAX_CONTENT_LENGTH'] = 900 * 1024 * 1024

# ========== FUNCTIONS ============
def is_valid_uuid_v4(header_uuid):
    try:
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
    with open(json_type_description_path, 'r') as f:
        json_type_description = json.loads(f.read())
    return json_type_description

# ========== ROUTES ============
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

    data_daily_uuid = []
    for result in daily_uuid:
        data_daily_uuid.append({"key": result[0], "value": int(result[1])})

    return jsonify(data_daily_uuid)

@app.route('/sensors_status')
def sensors_status():
    date = datetime.datetime.now().strftime("%Y%m%d")
    daily_uuid = redis_server_metadata.zrange('daily_uuid:{}'.format(date), 0, -1)

    status_daily_uuid = []
    for result in daily_uuid:
        first_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'first_seen')
        first_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(first_seen)))
        last_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'last_seen')
        last_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_seen)))
        if redis_server_metadata.sismember('blacklist_ip_by_uuid', result):
            Error = "All IP using this UUID are Blacklisted"
        elif redis_server_metadata.sismember('blacklist_uuid', result):
            Error = "Blacklisted UUID"
        else:
            Error = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'Error')

        if first_seen is not None and last_seen is not None:
            status_daily_uuid.append({"uuid": result,"first_seen": first_seen, "last_seen": last_seen,
                                        "first_seen_gmt": first_seen_gmt, "last_seen_gmt": last_seen_gmt, "Error": Error})

    return render_template("sensors_status.html", status_daily_uuid=status_daily_uuid)

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
    for type in redis_server_metadata.smembers('server:accepted_type'):
        list_accepted_types.append({"id": int(type), "description": json_type_description[int(type)]['description']})

    return render_template("server_management.html", list_accepted_types=list_accepted_types,
                            blacklisted_ip=blacklisted_ip, unblacklisted_ip=unblacklisted_ip,
                            blacklisted_uuid=blacklisted_uuid, unblacklisted_uuid=unblacklisted_uuid)

@app.route('/uuid_management')
def uuid_management():
    uuid_sensor = request.args.get('uuid')
    if is_valid_uuid_v4(uuid_sensor):

        first_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'first_seen')
        first_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(first_seen)))
        last_seen = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'last_seen')
        last_seen_gmt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_seen)))
        Error = redis_server_metadata.hget('metadata_uuid:{}'.format(uuid_sensor), 'Error')
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
        data_uuid= {"first_seen": first_seen, "last_seen": last_seen,
                    "blacklisted_uuid": blacklisted_uuid, "blacklisted_ip_by_uuid": blacklisted_ip_by_uuid,
                    "first_seen_gmt": first_seen_gmt, "last_seen_gmt": last_seen_gmt, "Error": Error}

        max_uuid_stream = redis_server_metadata.hget('stream_max_size_by_uuid', uuid_sensor)
        if max_uuid_stream is not None:
            max_uuid_stream = int(max_uuid_stream)
        else:
            max_uuid_stream = default_max_entries_by_stream

        return render_template("uuid_management.html", uuid_sensor=uuid_sensor, data_uuid=data_uuid, max_uuid_stream=max_uuid_stream)
    else:
        return 'Invalid uuid'

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
    if is_valid_uuid_v4(uuid_sensor):
        res = redis_server_metadata.srem('blacklist_uuid', uuid_sensor)
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
    else:
        if user:
            return redirect(url_for('server_management', blacklisted_ip=0))
        return 'Invalid ip'

@app.route('/unblacklist_ip')
def unblacklist_ip():
    ip = request.args.get('ip')
    user = request.args.get('redirect')
    if is_valid_ip(ip):
        res = redis_server_metadata.srem('blacklist_ip', ip)
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
    user = request.args.get('redirect')
    json_type_description = get_json_type_description()
    if json_type_description[int(type)]:
        redis_server_metadata.sadd('server:accepted_type', type)
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

# demo function
@app.route('/delete_data')
def delete_data():
    date = datetime.datetime.now().strftime("%Y%m%d")
    redis_server_metadata.delete('daily_type:{}'.format(date))
    redis_server_metadata.delete('daily_uuid:{}'.format(date))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, threaded=True)
