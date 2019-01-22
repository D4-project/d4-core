#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import uuid
import time
import redis
import flask
import datetime

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for

baseUrl = ''
if baseUrl != '':
    baseUrl = '/'+baseUrl

host_redis_stream = "localhost"
port_redis_stream = 6379

default_max_entries_by_stream = 10000

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
    return render_template("server_management.html")

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

@app.route('/blacklist_uuid')
def blacklist_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.sadd('blacklist_uuid', uuid_sensor)
        if user:
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

@app.route('/unblacklist_uuid')
def unblacklist_uuid():
    uuid_sensor = request.args.get('uuid')
    user = request.args.get('redirect')
    if is_valid_uuid_v4(uuid_sensor):
        redis_server_metadata.srem('blacklist_uuid', uuid_sensor)
        if user:
            return redirect(url_for('uuid_management', uuid=uuid_sensor))
    else:
        return 'Invalid uuid'

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

# demo function
@app.route('/delete_data')
def delete_data():
    date = datetime.datetime.now().strftime("%Y%m%d")
    redis_server_metadata.delete('daily_type:{}'.format(date))
    redis_server_metadata.delete('daily_uuid:{}'.format(date))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, threaded=True)
