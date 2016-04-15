#!/bin/bash
#Stop a docker process based on infrasim:[tag] image

while getopts "hn:" args;do
    case ${args} in
        h)
            echo "$0 -n <docker_name>"
            exit 1
            ;;
        n)
            docker_name=$OPTARG
            ;;
        *)
            echo "$0 -n <docker_name>"
            exit 1
            ;;
    esac
done

if [ -z "$docker_name" ]; then
	echo "Please give a name for docker process"
	exit 1
fi

existing_container=$(docker ps | grep ${docker_name})
if [ -z "$existing_container" ]; then
	echo "Your specified docker is not running!!!"
	exit 1
fi;


stop_docker() {
	running_container=$(docker ps | grep ${docker_name} | cut -d' ' -f 1)
	docker stop ${running_container}
}

stop_docker
