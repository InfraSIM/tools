#!/bin/bash
#Remove a docker container

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

existing_container=$(docker ps -a | grep ${docker_name})
if [ -z "$existing_container" ]; then
	echo "Your specified docker is not exist!!!"
	exit 1
fi;


rm_docker() {
	existing_container=$(docker ps -a| grep ${docker_name} | cut -d' ' -f 1)
	docker stop ${existing_container}
	docker rm ${existing_container}
}

rm_docker
