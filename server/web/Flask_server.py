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
    return render_template("index.html")

@app.route('/_json_daily_uuid_stats')
def _json_daily_uuid_stats():
    date = datetime.datetime.now().strftime("%Y%m%d")
    daily_uuid = redis_server_metadata.zrange('daily_uuid:{}'.format(date), 0, -1, withscores=True)

    data_daily_uuid = []
    for result in daily_uuid:
        data_daily_uuid.append({"key": result[0], "value": int(result[1])})

    return jsonify(data_daily_uuid)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, threaded=True)
