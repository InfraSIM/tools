#!/bin/bash

DOCKER_IMAGE_NAME="infrasim/infrasim-compute"
OVS_BRIDGE_NAME="ovs-br0"

help()
{
echo "cleanup.sh - help you to cleanup infrasim docker environment"
echo "Usage: sudo ./cleanup.sh"
}

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

if [ "$1" == "-h" -o "$1" == "--help" ]; then
    help
    exit 0
fi

# Stop and remove all containers with ancestor image: infrasim/infrasim-compute 
CONTAINERS=$(docker ps -a -q --filter ancestor=$DOCKER_IMAGE_NAME --format="{{.ID}}")

if [ "$CONTAINERS" != "" ]; then
    echo "Stop docker containers..."
    docker stop $CONTAINERS
    echo "Remove docker containers..."
    docker rm $CONTAINERS
else
    echo "No existing infrasim/infrasim-compute containers."
fi

# Delete Openvswitch "ovs-br0" if exists
ovs-vsctl br-exists $OVS_BRIDGE_NAME
if [ $? -eq 0 ]; then
    echo "Delete Openvswitch $OVS_BRIDGE_NAME ..."
    ovs-vsctl del-br $OVS_BRIDGE_NAME
fi

