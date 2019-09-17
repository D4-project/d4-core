#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import time
import redis
import bcrypt
import random

from flask_login import UserMixin

class User(UserMixin):

    def __init__(self, id):
        host_redis_metadata = os.getenv('D4_REDIS_METADATA_HOST', "localhost")
        port_redis_metadata = int(os.getenv('D4_REDIS_METADATA_PORT', 6380))

        self.r_serv_db = redis.StrictRedis(
            host=host_redis_metadata,
            port=port_redis_metadata,
            db=1,
            decode_responses=True)

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
