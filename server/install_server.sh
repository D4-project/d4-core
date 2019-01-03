#!/bin/bash

set -e
set -x

sudo apt-get install python3-pip -y
python3 -m pip install -r requirement.txt

# REDIS #
test ! -d redis/ && git clone https://github.com/antirez/redis.git
pushd redis/
git checkout 5.0
make
popd
