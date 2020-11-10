#!/usr/bin/env python3
# -*-coding:UTF-8 -*

'''
    Flask functions and routes for all D4 sensors
'''

import os
import re
import sys
import redis

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib'))
import ConfigLoader
import Sensor

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response
from flask_login import login_required, current_user

from Role_Manager import login_admin, login_user_basic

# ============ BLUEPRINT ============

D4_sensors = Blueprint('D4_sensors', __name__, template_folder='templates')

# ============ VARIABLES ============

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_metadata = config_loader.get_redis_conn("Redis_METADATA")
r_serv_db = config_loader.get_redis_conn("Redis_SERV")
config_loader = None
###  ###

# ============ FUNCTIONS ============


# ============= ROUTES ==============

@D4_sensors.route("/sensors/monitoring/add", methods=['GET'])
@login_required
@login_user_basic
def add_sensor_to_monitor():
    sensor_uuid = request.args.get("uuid")
    return render_template("sensors/add_sensor_to_monitor.html",
                                sensor_uuid=sensor_uuid)

@D4_sensors.route("/sensors/monitoring/add_post", methods=['POST'])
@login_required
@login_user_basic
def add_sensor_to_monitor_post():
    sensor_uuid = request.form.get("uuid")
    delta_time = request.form.get("delta_time")
    res = Sensor.api_add_sensor_to_monitor({'uuid':sensor_uuid, 'delta_time': delta_time})
    if res:
        Response(json.dumps(res[0], indent=2, sort_keys=True), mimetype='application/json'), res[1]
    return redirect(url_for('uuid_management', uuid=sensor_uuid))

@D4_sensors.route("/sensors/monitoring/delete", methods=['GET'])
@login_required
@login_user_basic
def delete_sensor_to_monitor():
    sensor_uuid = request.args.get("uuid")
    res = Sensor.api_delete_sensor_to_monitor({'uuid':sensor_uuid})
    if res:
        Response(json.dumps(res[0], indent=2, sort_keys=True), mimetype='application/json'), res[1]
    return redirect(url_for('uuid_management', uuid=sensor_uuid))


#
#
#
#
#
#
#
#
