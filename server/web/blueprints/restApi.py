#!/usr/bin/env python3
# -*-coding:UTF-8 -*

'''
    Flask functions and routes for the rest api
'''

import os
import re
import sys
import time
import uuid
import json
import redis
import random
import datetime

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response
from flask_login import login_required

from functools import wraps

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib'))
import Sensor
import ConfigLoader

# ============ BLUEPRINT ============

restApi = Blueprint('restApi', __name__, template_folder='templates')

# ============ VARIABLES ============

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_metadata = config_loader.get_redis_conn("Redis_METADATA")
r_serv_db = config_loader.get_redis_conn("Redis_SERV")
r_cache = config_loader.get_redis_conn("Redis_CACHE")
config_loader = None
###  ###

# ============ AUTH FUNCTIONS ============

def check_token_format(strg, search=re.compile(r'[^a-zA-Z0-9_-]').search):
    return not bool(search(strg))

def verify_token(token):
    if len(token) != 41:
        return False

    if not check_token_format(token):
        return False

    rand_sleep = random.randint(1,300)/1000
    time.sleep(rand_sleep)
    if r_serv_db.hexists('user:tokens', token):
        return True
    else:
        return False

def get_user_from_token(token):
    return r_serv_db.hget('user:tokens', token)

def verify_user_role(role, token):
    user_id = get_user_from_token(token)
    if user_id:
        if is_in_role(user_id, role):
            return True
        else:
            return False
    else:
        return False

def is_in_role(user_id, role):
    if r_serv_db.sismember('user_role:{}'.format(role), user_id):
        return True
    else:
        return False

# ============ DECORATOR ============

def token_required(user_role):
    def actual_decorator(funct):
        @wraps(funct)
        def api_token(*args, **kwargs):
            data = authErrors(user_role)
            if data:
                return Response(json.dumps(data[0], indent=2, sort_keys=True), mimetype='application/json'), data[1]
            else:
                return funct(*args, **kwargs)
        return api_token
    return actual_decorator

def get_auth_from_header():
    token = request.headers.get('Authorization').replace(' ', '') # remove space
    return token

def authErrors(user_role):
    # Check auth
    if not request.headers.get('Authorization'):
        return ({'status': 'error', 'reason': 'Authentication needed'}, 401)
    token = get_auth_from_header()
    data = None
    # verify token format

    # brute force protection
    current_ip = request.remote_addr
    login_failed_ip = r_cache.get('failed_login_ip_api:{}'.format(current_ip))
    # brute force by ip
    if login_failed_ip:
        login_failed_ip = int(login_failed_ip)
        if login_failed_ip >= 5:
            return ({'status': 'error', 'reason': 'Max Connection Attempts reached, Please wait {}s'.format(r_cache.ttl('failed_login_ip_api:{}'.format(current_ip)))}, 401)

    try:
        authenticated = False
        if verify_token(token):
            authenticated = True

            # check user role
            if not verify_user_role(user_role, token):
                data = ({'status': 'error', 'reason': 'Access Forbidden'}, 403)

        if not authenticated:
            r_cache.incr('failed_login_ip_api:{}'.format(current_ip))
            r_cache.expire('failed_login_ip_api:{}'.format(current_ip), 300)
            data = ({'status': 'error', 'reason': 'Authentication failed'}, 401)
    except Exception as e:
        print(e)
        data = ({'status': 'error', 'reason': 'Malformed Authentication String'}, 400)
    if data:
        return data
    else:
        return None

# ============ FUNCTIONS ============

def is_valid_uuid_v4(header_uuid):
    try:
        header_uuid=header_uuid.replace('-', '')
        uuid_test = uuid.UUID(hex=header_uuid, version=4)
        return uuid_test.hex == header_uuid
    except:
        return False

def one():
    return 1

# ============= ROUTES ==============


@restApi.route("/api/v1/add/sensor/register", methods=['POST'])
@token_required('sensor_register')
def add_sensor_register():
    data = request.get_json()
    res = Sensor.register_sensor(data)
    return Response(json.dumps(res[0], indent=2, sort_keys=True), mimetype='application/json'), res[1]
