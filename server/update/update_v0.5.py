#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import os
import sys
import datetime
import time
import uuid
import redis

sys.path.append(os.path.join(os.environ['D4_HOME'], 'lib/'))
import ConfigLoader
import Analyzer_Queue
import d4_type

### Config ###
config_loader = ConfigLoader.ConfigLoader()
r_serv_metadata = config_loader.get_redis_conn("Redis_METADATA")
config_loader = None
###  ###

if __name__ == '__main__':

    for format_type in d4_type.get_all_accepted_format_type():
        format_type = int(format_type)
        for queue_uuid in Analyzer_Queue.get_all_queues_by_type(format_type):
            r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'type', format_type)
            r_serv_metadata.sadd('all:analyzer:format_type', format_type)
            r_serv_metadata.sadd('all:analyzer:by:format_type:{}'.format(format_type), queue_uuid)

    for extended_type in d4_type.get_all_accepted_extended_type():
        for queue_uuid in Analyzer_Queue.get_all_queues_by_extended_type(extended_type):
            r_serv_metadata.hset('analyzer:{}'.format(queue_uuid), 'metatype', extended_type)
            r_serv_metadata.sadd('all:analyzer:extended_type', extended_type)
            r_serv_metadata.sadd('all:analyzer:format_type', 254)
            r_serv_metadata.sadd('all:analyzer:by:extended_type:{}'.format(extended_type), queue_uuid)
            r_serv_metadata.sadd('all:analyzer:by:format_type:254', queue_uuid)
