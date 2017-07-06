#!/bin/bash

LOG_FILE=$PWD"/docker.log" #Docker log file location
# TODO: need to assign existing network interface of the running machine
NETWORK="ens224"  #Host DHCP Server interface
DOCKER_IMG_NAME="infrasim/infrasim-compute" #Docker image name
DOCKER_IMG_TAG="latest" #Docker image tag
NAME="infrasim" #Container Name
PORT="5901" #Host port which is bind to container port
RET=0 #Return code of command in log_and_exec

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

help()
{
    echo "docker.sh - setup environment and run infrasim container in your host."
    echo "Usage: sudo ./docker.sh [options]"
    echo "Options:"
    echo "-i Specify a host interface to bind the container network"
    echo "-t Specify the tag to pull docker image"
    echo "-p The host port used to map the container's vnc port"
    echo "-n Set the name for the container"
}

log()
{
    echo -e ${PRX}"$(date "+%b %d %T") : $@" >> $LOG_FILE
}

log_and_exec()
{
    log "$@"
    OUTPUT=$(eval "$@" 2>&1)
    RET=$?
    if [ "$OUTPUT" != "" ]; then
        echo $OUTPUT | tee -a $LOG_FILE
    fi
}

while getopts "hi:t:p:n:" args;do
    case ${args} in
        h)
            help
	        exit 0
            ;;
        i)
            NETWORK=$OPTARG
	        ;;
        t)
            DOCKER_IMG_TAG=$OPTARG
	        ;;
        p)
            PORT=$OPTARG
            ;;
        n)
            NAME=$OPTARG
            ;;
        *)
            help
	        exit 1
	        ;;
    esac
done	

# Prepare for docker environment
if [ -f $LOG_FILE ]; then
    log_and_exec "rm $LOG_FILE"
fi
echo "Check if docker exists:"
log_and_exec "which docker"
if [ $RET -ne 0 ]; then
    echo "Going to install docker..."
    log_and_exec "apt-get remove docker docker-engine"
    log_and_exec "apt-get update"
    log_and_exec "apt-get install -y apt-transport-https ca-certificates curl software-properties-common"
    log_and_exec "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -"
    log_and_exec "sudo apt-key fingerprint 0EBFCD88"
    log_and_exec "sudo add-apt-repository \"deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\""
    log_and_exec "apt-get update"
    log_and_exec "apt-get install -y docker-ce"
    which docker
    if [ $? -eq 0 ]; then
        echo "Successfully installed docker."
    else
        echo "Failed to install docker, please install it manually then continue with the script."
    fi
else
    echo "Docker already installed; Version: $(docker --version)"
fi

# Setup the host network
log_and_exec "apt-get install -y openvswitch-switch"
log_and_exec "ovs-vsctl br-exists ovs-br0"
if [ $RET -ne 0 ]; then
    log_and_exec "ovs-vsctl add-br ovs-br0"
fi
PORTS=$(ovs-vsctl list-ports ovs-br0)
if [[ " ${PORTS[*]} " == *"$NETWORK"* ]]; then
    echo "$NETWORK is a port on ovs-br0"
else
    log_and_exec "ovs-vsctl add-port ovs-br0 $NETWORK"
fi
log_and_exec "ip link set dev ovs-br0 up"

# Setup docker container network
log_and_exec "docker images $DOCKER_IMG_NAME:$DOCKER_IMG_TAG"
log_and_exec "docker ps -a |grep -w $NAME"
if [ $RET -eq 0 ]; then
    echo "Going to stop and remove container $NAME because it's running."
    log_and_exec "docker container stop $NAME"
    log_and_exec "docker container rm $NAME"
fi
log_and_exec "docker pull $DOCKER_IMG_NAME:$DOCKER_IMG_TAG"
if [ $RET -ne 0 ]; then
    echo "Failed to pull $DOCKER_IMG_NAME:$DOCKER_IMG_TAG from dockerhub."
    exit 1
fi

# Clone pipework for network configuration
log_and_exec "docker run --privileged -p $PORT:5901 -dit --name $NAME $DOCKER_IMG_NAME:$DOCKER_IMG_TAG /bin/bash"
log_and_exec "which pipework"
if [ $RET -ne 0 ]; then
    log_and_exec "git clone -c http.sslVerify=false https://github.com/jpetazzo/pipework.git"
    log_and_exec "cp $PWD/pipework/pipework /usr/local/bin/pipework"
    log_and_exec "chmod +x /usr/local/bin/pipework"
else
    echo "pipework already exists, so not install it."
fi
log_and_exec "/bin/bash $PWD/pipework/pipework ovs-br0 -i eth1 $NAME dhclient"
log_and_exec "docker exec $NAME brctl addbr br0"
log_and_exec "docker exec $NAME brctl addif br0 eth1"
IP=$(docker exec $NAME ifconfig eth1 | awk '/inet addr/{print substr($2,6)}')
if [ $? -ne 0 ]; then
    echo "No DHCP service, please check DHCP server."
else
    echo "IP assigned for eth1 is: $IP"
    log_and_exec "docker exec $NAME ifconfig eth1 0.0.0.0"
    log_and_exec "docker exec $NAME ifconfig br0 $IP"
fi
log_and_exec "docker exec $NAME infrasim node start"
