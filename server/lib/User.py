#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import time
import redis
import bcrypt
import random

from flask_login import UserMixin

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader

config_loader = ConfigLoader.ConfigLoader()
r_serv_db = config_loader.get_redis_conn("Redis_SERV")
config_loader = None

# CONFIG #
config_loader = ConfigLoader.ConfigLoader()

class User(UserMixin):

    def __init__(self, id):

        self.r_serv_db = r_serv_db

        if self.r_serv_db.hexists('user:all', id):
            self.id = id
        else:
            self.id = "__anonymous__"

    # return True or False
    #def is_authenticated():

    # return True or False
    #def is_anonymous():

    @classmethod
    def get(self_class, id):
        return self_class(id)

    def user_is_anonymous(self):
        if self.id == "__anonymous__":
            return True
        else:
            return False

    def check_password(self, password):
        if self.user_is_anonymous():
            return False

        rand_sleep = random.randint(1,300)/1000
        time.sleep(rand_sleep)

        password = password.encode()
        hashed_password = self.r_serv_db.hget('user:all', self.id).encode()
        if bcrypt.checkpw(password, hashed_password):
            return True
        else:
            return False

    def request_password_change(self):
        if self.r_serv_db.hget('user_metadata:{}'.format(self.id), 'change_passwd') == 'True':
            return True
        else:
            return False

    def is_in_role(self, role):
        if self.r_serv_db.sismember('user_role:{}'.format(role), self.id):
            return True
        else:
            return False
