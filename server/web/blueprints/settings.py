#!/usr/bin/env python3
# -*-coding:UTF-8 -*

'''
    Flask functions and routes for the rest api
'''

import os
import re
import sys
import redis

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response
from flask_login import login_required, current_user

from Role_Manager import login_admin, login_user_basic
from Role_Manager import create_user_db, edit_user_db, delete_user_db, check_password_strength, generate_new_token, gen_password, get_all_role

# ============ BLUEPRINT ============

settings = Blueprint('settings', __name__, template_folder='templates')

# ============ VARIABLES ============

email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}'
email_regex = re.compile(email_regex)
host_redis_metadata = os.getenv('D4_REDIS_METADATA_HOST', "localhost")
port_redis_metadata = int(os.getenv('D4_REDIS_METADATA_PORT', 6380))

r_serv_metadata = redis.StrictRedis(
                host=host_redis_metadata,
                port=port_redis_metadata,
                db=0,
                decode_responses=True)

r_serv_db = redis.StrictRedis(
                host=host_redis_metadata,
                port=port_redis_metadata,
                db=1,
                decode_responses=True)

# ============ FUNCTIONS ============

def one():
    return 1

def check_email(email):
    result = email_regex.match(email)
    if result:
        return True
    else:
        return False

def get_user_metadata(user_id):
    user_metadata = {}
    user_metadata['email'] = user_id
    user_metadata['role'] = r_serv_db.hget('user_metadata:{}'.format(user_id), 'role')
    user_metadata['api_key'] = r_serv_db.hget('user_metadata:{}'.format(user_id), 'token')
    return user_metadata

def get_users_metadata(list_users):
    users = []
    for user in list_users:
        users.append(get_user_metadata(user))
    return users

def get_all_users():
    return r_serv_db.hkeys('user:all')


# ============= ROUTES ==============

@settings.route("/settings/", methods=['GET'])
@login_required
@login_user_basic
def settings_page():
    return redirect(url_for('settings.edit_profile'))

@settings.route("/settings/edit_profile", methods=['GET'])
@login_required
@login_user_basic
def edit_profile():
    user_metadata = get_user_metadata(current_user.get_id())
    admin_level = current_user.is_in_role('admin')
    return render_template("edit_profile.html", user_metadata=user_metadata,
                            admin_level=admin_level)

@settings.route("/settings/new_token", methods=['GET'])
@login_required
@login_user_basic
def new_token():
    generate_new_token(current_user.get_id())
    return redirect(url_for('settings.edit_profile'))

@settings.route("/settings/new_token_user", methods=['GET'])
@login_required
@login_admin
def new_token_user():
    user_id = request.args.get('user_id')
    if r_serv_db.exists('user_metadata:{}'.format(user_id)):
        generate_new_token(user_id)
    return redirect(url_for('settings.users_list'))

@settings.route("/settings/create_user", methods=['GET'])
@login_required
@login_admin
def create_user():
    user_id = request.args.get('user_id')
    error = request.args.get('error')
    error_mail = request.args.get('error_mail')
    role = None
    if r_serv_db.exists('user_metadata:{}'.format(user_id)):
        role = r_serv_db.hget('user_metadata:{}'.format(user_id), 'role')
    else:
        user_id = None
    all_roles = get_all_role()
    return render_template("create_user.html", all_roles=all_roles, user_id=user_id, user_role=role,
                                        error=error, error_mail=error_mail,
                                        admin_level=True)

@settings.route("/settings/create_user_post", methods=['POST'])
@login_required
@login_admin
def create_user_post():
    email = request.form.get('username')
    role = request.form.get('user_role')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')

    all_roles = get_all_role()

    if email and len(email)< 300 and check_email(email) and role:
        if role in all_roles:
            # password set
            if password1 and password2:
                if password1==password2:
                    if check_password_strength(password1):
                        password = password1
                    else:
                        return render_template("create_user.html", all_roles=all_roles, error="Incorrect Password", admin_level=True)
                else:
                    return render_template("create_user.html", all_roles=all_roles, error="Passwords don't match", admin_level=True)
            # generate password
            else:
                password = gen_password()

            if current_user.is_in_role('admin'):
                # edit user
                if r_serv_db.exists('user_metadata:{}'.format(email)):
                    if password1 and password2:
                        edit_user_db(email, password=password, role=role)
                        return redirect(url_for('settings.users_list', new_user=email, new_user_password=password, new_user_edited=True))
                    else:
                        edit_user_db(email, role=role)
                        return redirect(url_for('settings.users_list', new_user=email, new_user_password='Password not changed', new_user_edited=True))
                # create user
                else:
                    create_user_db(email, password, default=True, role=role)
                    return redirect(url_for('settings.users_list', new_user=email, new_user_password=password, new_user_edited=False))

        else:
            return render_template("create_user.html", all_roles=all_roles, admin_level=True)
    else:
        return render_template("create_user.html", all_roles=all_roles, error_mail=True, admin_level=True)

@settings.route("/settings/users_list", methods=['GET'])
@login_required
@login_admin
def users_list():
    all_users = get_users_metadata(get_all_users())
    new_user = request.args.get('new_user')
    new_user_dict = {}
    if new_user:
        new_user_dict['email'] = new_user
        new_user_dict['edited'] = request.args.get('new_user_edited')
        new_user_dict['password'] = request.args.get('new_user_password')
    return render_template("users_list.html", all_users=all_users, new_user=new_user_dict, admin_level=True)

@settings.route("/settings/edit_user", methods=['GET'])
@login_required
@login_admin
def edit_user():
    user_id = request.args.get('user_id')
    return redirect(url_for('settings.create_user', user_id=user_id))

@settings.route("/settings/delete_user", methods=['GET'])
@login_required
@login_admin
def delete_user():
    user_id = request.args.get('user_id')
    delete_user_db(user_id)
    return redirect(url_for('settings.users_list'))
