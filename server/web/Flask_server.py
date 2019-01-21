#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
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
        Error = redis_server_metadata.hget('metadata_uuid:{}'.format(result), 'Error')
        if first_seen is not None and last_seen is not None:
            status_daily_uuid.append({"uuid": result,"first_seen": first_seen, "last_seen": last_seen,
                                        "first_seen_gmt": first_seen_gmt, "last_seen_gmt": last_seen_gmt, "Error": Error})

    return render_template("sensors_status.html", status_daily_uuid=status_daily_uuid)

# demo function
@app.route('/delete_data')
def delete_data():
    date = datetime.datetime.now().strftime("%Y%m%d")
    redis_server_metadata.delete('daily_type:{}'.format(date))
    redis_server_metadata.delete('daily_uuid:{}'.format(date))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, threaded=True)
