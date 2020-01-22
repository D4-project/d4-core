#!/bin/bash

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"
ROSE="\\033[1;35m"
BLUE="\\033[1;34m"
WHITE="\\033[0;02m"
YELLOW="\\033[1;33m"
CYAN="\\033[1;36m"

. ./D4ENV/bin/activate

isredis=`screen -ls | egrep '[0-9]+.Redis_D4	' | cut -d. -f1`
isd4server=`screen -ls | egrep '[0-9]+.Server_D4	' | cut -d. -f1`
isworker=`screen -ls | egrep '[0-9]+.Workers_D4	' | cut -d. -f1`
isflask=`screen -ls | egrep '[0-9]+.Flask_D4	' | cut -d. -f1`

function helptext {
    echo -e $YELLOW"
         _______   __    __                                                                   __
        /       \ /  |  /  |                                                                 /  |
        \$\$\$\$\$\$\$  |\$\$ |  \$\$ |        ______    ______    ______      __   ______    _______  _\$\$ |_
        \$\$ |  \$\$ |\$\$ |__\$\$ |       /      \  /      \  /      \    /  | /      \  /       |/ \$\$   |
        \$\$ |  \$\$ |\$\$    \$\$ |      /\$\$\$\$\$\$  |/\$\$\$\$\$\$  |/\$\$\$\$\$\$  |   \$\$/ /\$\$\$\$\$\$  |/\$\$\$\$\$\$\$/ \$\$\$\$\$\$/
        \$\$ |  \$\$ |\$\$\$\$\$\$\$\$ |      \$\$ |  \$\$ |\$\$ |  \$\$/ \$\$ |  \$\$ |   /  |\$\$    \$\$ |\$\$ |        \$\$ | __
        \$\$ |__\$\$ |      \$\$ |      \$\$ |__\$\$ |\$\$ |      \$\$ \__\$\$ |   \$\$ |\$\$\$\$\$\$\$\$/ \$\$ \_____   \$\$ |/  |
        \$\$    \$\$/       \$\$ |      \$\$    \$\$/ \$\$ |      \$\$    \$\$/    \$\$ |\$\$       |\$\$       |  \$\$  \$\$/
        \$\$\$\$\$\$\$/        \$\$/       \$\$\$\$\$\$\$/  \$\$/        \$\$\$\$\$\$/__   \$\$ | \$\$\$\$\$\$\$/  \$\$\$\$\$\$\$/    \$\$\$\$/
                                  \$\$ |                       /  \__\$\$ |
                                  \$\$ |                       \$\$    \$\$/
                                  \$\$/                         \$\$\$\$\$\$/

    "$DEFAULT"
    This script launch:    (Inside screen Daemons)"$CYAN"
      - D4 Twisted server.
      - All wokers manager.
      - All Redis in memory servers.
      - Flask server.

    Usage:    LAUNCH.sh
                  [-l | --launchAuto]
                  [-k | --killAll]
                  [-h | --help]
    "
}

CONFIG=$D4_HOME/configs/server.conf
redis_stream=`sed -nr '/\[Redis_STREAM\]/,/\[/{/port/p}' ${CONFIG} | awk -F= '/port/{print $2}' | sed 's/ //g'`
redis_metadata=`sed -nr '/\[Redis_METADATA\]/,/\[/{/port/p}' ${CONFIG} | awk -F= '/port/{print $2}' | sed 's/ //g'`

function launching_redis {
    conf_dir="${D4_HOME}/configs/"
    redis_dir="${D4_HOME}/redis/src/"

    screen -dmS "Redis_D4"
    sleep 0.1
    echo -e $GREEN"\t* Launching D4 Redis Servers"$DEFAULT
    screen -S "Redis_D4" -X screen -t "6379" bash -c $redis_dir'redis-server '$conf_dir'6379.conf ; read x'
    sleep 0.1
    screen -S "Redis_D4" -X screen -t "6380" bash -c $redis_dir'redis-server '$conf_dir'6380.conf ; read x'
    sleep 0.1
}

function launching_d4_server {
    screen -dmS "Server_D4"
    sleep 0.1
    echo -e $GREEN"\t* Launching D4 Server"$DEFAULT

    screen -S "Server_D4" -X screen -t "Server_D4" bash -c "cd ${D4_HOME}; ./server.py -v 10; read x"
    sleep 0.1
}

function launching_workers {
    screen -dmS "Workers_D4"
    sleep 0.1
    echo -e $GREEN"\t* Launching D4 Workers"$DEFAULT

    screen -S "Workers_D4" -X screen -t "1_workers" bash -c "cd ${D4_HOME}/workers/workers_1; ./workers_manager.py; read x"
    sleep 0.1
    screen -S "Workers_D4" -X screen -t "2_workers" bash -c "cd ${D4_HOME}/workers/workers_2; ./workers_manager.py; read x"
    sleep 0.1
    screen -S "Workers_D4" -X screen -t "2_workers" bash -c "cd ${D4_HOME}/workers/workers_3; ./workers_manager.py; read x"
    sleep 0.1
    screen -S "Workers_D4" -X screen -t "4_workers" bash -c "cd ${D4_HOME}/workers/workers_4; ./workers_manager.py; read x"
    sleep 0.1
    screen -S "Workers_D4" -X screen -t "8_workers" bash -c "cd ${D4_HOME}/workers/workers_8; ./workers_manager.py; read x"
    sleep 0.1
}

function shutting_down_redis {
    redis_dir=${D4_HOME}/redis/src/
    bash -c $redis_dir'redis-cli -p '$redis_stream' SHUTDOWN'
    sleep 0.1
    bash -c $redis_dir'redis-cli -p '$redis_metadata' SHUTDOWN'
    sleep 0.1
}

function checking_redis {
    flag_redis=0
    redis_dir=${D4_HOME}/redis/src/
    bash -c $redis_dir'redis-cli -p '$redis_stream' PING | grep "PONG" &> /dev/null'
    if [ ! $? == 0 ]; then
       echo -e $RED"\t6379 not ready"$DEFAULT
       flag_redis=1
    fi
    sleep 0.1
    bash -c $redis_dir'redis-cli -p '$redis_metadata' PING | grep "PONG" &> /dev/null'
    if [ ! $? == 0 ]; then
       echo -e $RED"\t6380 not ready"$DEFAULT
       flag_redis=1
    fi
    sleep 0.1

    return $flag_redis;
}

function wait_until_redis_is_ready {
    redis_not_ready=true
    while $redis_not_ready; do
        if checking_redis; then
            redis_not_ready=false;
        else
            sleep 1
        fi
    done
    echo -e $YELLOW"\t* Redis Launched"$DEFAULT
}

function launch_redis {
    if [[ ! $isredis ]]; then
        launching_redis;
    else
        echo -e $RED"\t* A D4_Redis screen is already launched"$DEFAULT
    fi
}

function launch_d4_server {
    if [[ ! $isd4server ]]; then
      sleep 1
        if checking_redis; then
            launching_d4_server;
        else
            echo -e $YELLOW"\tD4 Redis not started, waiting 5 more secondes"$DEFAULT
            sleep 5
            if checking_redis; then
                launching_d4_server;
            else
                echo -e $RED"\tError: Redis not started"$DEFAULT
                exit 1
            fi;
        fi;
    else
        echo -e $RED"\t* A Server_D4 screen is already launched"$DEFAULT
    fi
}

function launch_workers {
    if [[ ! $isworker ]]; then
      sleep 1
        if checking_redis; then
            launching_workers;
        else
            echo -e $YELLOW"\tD4 Redis not started, waiting 5 more secondes"$DEFAULT
            sleep 5
            if checking_redis; then
                launching_workers;
            else
                echo -e $RED"\tError: Redis not started"$DEFAULT
                exit 1
            fi;
        fi;
    else
        echo -e $RED"\t* A Workers_D4 screen is already launched"$DEFAULT
    fi
}

function launch_flask {
    if [[ ! $isflask ]]; then
        flask_dir=${D4_HOME}/web
        screen -dmS "Flask_D4"
        sleep 0.1
        echo -e $GREEN"\t* Launching Flask server"$DEFAULT
        # screen -S "Flask_D4" -X screen -t "Flask_server" bash -c "cd $flask_dir; export FLASK_DEBUG=1;export FLASK_APP=Flask_server.py; python -m flask run --port 7000; read x"
        screen -S "Flask_D4" -X screen -t "Flask_server" bash -c "cd $flask_dir; ls; ./Flask_server.py; read x"
    else
        echo -e $RED"\t* A Flask_D4 screen is already launched"$DEFAULT
    fi
}

function killall {


    if [[ $isredis || $isd4server || $isworker || $isflask ]]; then
        echo -e $GREEN"\t* Gracefully closing D4 Servers ..."$DEFAULT
        kill -SIGINT $isd4server
        sleep 3
        kill $isd4server $isflask
        echo -e $GREEN"\t* Gracefully closing D4 Workers ..."$DEFAULT
        kill -SIGINT $isworker
        sleep 0.5
        kill $isworker
        echo -e $GREEN"\t* $isd4server $isworker $isflask killed."$DEFAULT
        echo -e $GREEN"\t* Gracefully closing redis servers ..."$DEFAULT
        shutting_down_redis;
        kill $isredis
        sleep 0.2
        echo -e $ROSE`screen -ls`$DEFAULT
    else
        echo -e $RED"\t* No screen to kill"$DEFAULT
    fi
}

function update_web {
    echo -e "\t* Updating web..."
    bash -c "(cd ${D4_HOME}/web; ./update_web.sh)"
    exitStatus=$?
    if [ $exitStatus -ge 1 ]; then
        echo -e $RED"\t* Web not up-to-date"$DEFAULT
        exit
    else
        echo -e $GREEN"\t* Web updated"$DEFAULT
    fi
}

function update_config {
    echo -e $GREEN"\t* Updating Config File"$DEFAULT
    bash -c "(cd ${D4_HOME}/configs; ./update_conf.py -v 0)"
}

function launch_all {
    helptext;
    launch_redis;
    update_config;
    launch_d4_server;
    launch_workers;
    launch_flask;
}

#If no params, display the menu
[[ $@ ]] || {

    helptext;

    options=("Redis" "D4-Server" "Workers-manager" "Flask" "Killall" "Update-web")

    menu() {
        echo "What do you want to Launch?:"
        for i in ${!options[@]}; do
            printf "%3d%s) %s\n" $((i+1)) "${choices[i]:- }" "${options[i]}"
        done
        [[ "$msg" ]] && echo "$msg"; :
    }

    prompt="Check an option (again to uncheck, ENTER when done): "
    while menu && read -rp "$prompt" numinput && [[ "$numinput" ]]; do
        for num in $numinput; do
            [[ "$num" != *[![:digit:]]* ]] && (( num > 0 && num <= ${#options[@]} )) || {
                msg="Invalid option: $num"; break
            }
            ((num--)); msg="${options[num]} was ${choices[num]:+un}checked"
            [[ "${choices[num]}" ]] && choices[num]="" || choices[num]="+"
        done
    done

    for i in ${!options[@]}; do
        if [[ "${choices[i]}" ]]; then
            case ${options[i]} in
                Redis)
                    launch_redis
                    ;;
                D4-Server)
                    launch_d4_server;
                    ;;
                Workers-manager)
                    launch_workers;
                    ;;
                Flask)
                    launch_flask;
                    ;;
                Killall)
                    killall;
                    ;;
                Update-web)
                    update_web;
                    ;;
            esac
        fi
    done

    exit
}

while [ "$1" != "" ]; do
    case $1 in
        -l | --launchAuto )           launch_all;
                                      ;;
        -k | --killAll )              helptext;
                                      killall;
                                      ;;
        -lrv | --launchRedisVerify )  launch_redis;
                                      wait_until_redis_is_ready;
                                      ;;
        -h | --help )                 helptext;
                                      exit
                                      ;;
        * )                           helptext
                                      exit 1
    esac
    shift
done
