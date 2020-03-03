#!/usr/bin/env python3
# -*-coding:UTF-8 -*

'''
    Flask functions and routes for the rest api
'''

import os
import re
import sys
import redis

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib'))
import ConfigLoader
import Analyzer_Queue

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response
from flask_login import login_required, current_user

from Role_Manager import login_admin, login_user_basic
from Role_Manager import create_user_db, edit_user_db, delete_user_db, check_password_strength, generate_new_token, gen_password, get_all_role

# ============ BLUEPRINT ============

analyzer_queue = Blueprint('analyzer_queue', __name__, template_folder='templates')

# ============ VARIABLES ============

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_metadata = config_loader.get_redis_conn("Redis_METADATA")
r_serv_db = config_loader.get_redis_conn("Redis_SERV")
config_loader = None
###  ###

# ============ FUNCTIONS ============


# ============= ROUTES ==============

@analyzer_queue.route("/analyzer_queue/create_queue", methods=['GET'])
@login_required
@login_user_basic
def create_analyzer_queue():
    return render_template("analyzer_queue/queue_creator.html")

@analyzer_queue.route("/analyzer_queue/create_queue_post", methods=['POST'])
@login_required
@login_user_basic
def create_analyzer_queue_post():
    l_queue_meta = ['analyzer_type', 'analyzer_metatype', 'description', 'analyzer_uuid']
    queue_type = request.form.get("analyzer_type")
    queue_metatype = request.form.get("analyzer_metatype")
    queue_description = request.form.get("description")
    queue_uuid = request.form.get("analyzer_uuid")

    queue_type = Analyzer_Queue.sanitize_queue_type(queue_type)

    # unpack uuid group
    l_uuid = set()
    l_invalid_uuid = set()
    for obj_tuple in list(request.form):
        if obj_tuple not in l_queue_meta:
            sensor_uuid = request.form.get(obj_tuple)
            if Analyzer_Queue.is_valid_uuid_v4(sensor_uuid):
                l_uuid.add(sensor_uuid)
            else:
                if sensor_uuid:
                    l_invalid_uuid.add(sensor_uuid)

    l_uuid = list(l_uuid)
    l_invalid_uuid = list(l_invalid_uuid)
    if l_invalid_uuid:
        return render_template("analyzer_queue/queue_creator.html", queue_uuid=queue_uuid, queue_type=queue_type, metatype_name=queue_metatype,
                                    description=queue_description, l_uuid=l_uuid, l_invalid_uuid=l_invalid_uuid)

    res = Analyzer_Queue.create_queues(queue_type, queue_uuid=queue_uuid, l_uuid=l_uuid, metatype_name=queue_metatype, description=queue_description)
    if isinstance(res,dict):
        return jsonify(res)
    if res:
        return redirect(url_for('server_management', _anchor=res))

@analyzer_queue.route("/analyzer_queue/edit_queue", methods=['GET'])
@login_required
@login_user_basic
def edit_queue_analyzer_queue():
    queue_uuid = request.args.get("queue_uuid")
    queue_metadata = Analyzer_Queue.get_queue_metadata(queue_uuid, is_group=True)
    if 'is_group_queue' in queue_metadata:
        l_sensors_uuid = Analyzer_Queue.get_queue_group_all_sensors(queue_uuid)
    else:
        l_sensors_uuid = None
    return render_template("analyzer_queue/queue_editor.html", queue_metadata=queue_metadata, l_sensors_uuid=l_sensors_uuid)

@analyzer_queue.route("/analyzer_queue/edit_queue_post", methods=['POST'])
@login_required
@login_user_basic
def edit_queue_analyzer_queue_post():
    l_queue_meta = ['queue_uuid', 'description']
    queue_uuid = request.form.get("queue_uuid")
    queue_description = request.form.get("description")

    l_uuid = set()
    l_invalid_uuid = set()
    for obj_tuple in list(request.form):
        if obj_tuple not in l_queue_meta:
            sensor_uuid = request.form.get(obj_tuple)
            if Analyzer_Queue.is_valid_uuid_v4(sensor_uuid):
                l_uuid.add(sensor_uuid)
            else:
                if sensor_uuid:
                    l_invalid_uuid.add(sensor_uuid)

    if l_invalid_uuid:
        queue_metadata = Analyzer_Queue.get_queue_metadata(queue_uuid, is_group=True)
        if queue_description:
            queue_metadata['description'] = queue_description
        return render_template("analyzer_queue/queue_editor.html", queue_metadata=queue_metadata, l_sensors_uuid=l_uuid, l_invalid_uuid=l_invalid_uuid)

    Analyzer_Queue.edit_queue_description(queue_uuid, queue_description)
    Analyzer_Queue.edit_queue_sensors_set(queue_uuid, l_uuid)

    return redirect(url_for('analyzer_queue.edit_queue_analyzer_queue', queue_uuid=queue_uuid))
