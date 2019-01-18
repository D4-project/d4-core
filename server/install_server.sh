#!/bin/bash

set -e
set -x

sudo apt-get install python3-pip virtualenv -y

if [ -z "$VIRTUAL_ENV" ]; then
    virtualenv -p python3 D4ENV
    echo export D4_HOME=$(pwd) >> ./D4ENV/bin/activate
    . ./D4ENV/bin/activate
fi
python3 -m pip install -r requirement.txt

pushd web/
./update_web.sh
popd


python3 -m pip install -r requirement.txt

# REDIS #
test ! -d redis/ && git clone https://github.com/antirez/redis.git
pushd redis/
git checkout 5.0
make
popd
