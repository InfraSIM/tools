#!/bin/bash

LOG_FILE=$PWD"/docker.log" #Docker log file location
NETWORK="ens224"  #Host DHCP Server interface
DOCKER_IMG_NAME="cxy4430/infrasim-compute" #Docker image name
DOCKER_IMG_TAG="0601" #Docker image tag
NAME="idic" #Container Name
PORT="5901" #Host port which is bind to container port

while getopts "hi:t:p:" args;do
    case ${args} in
	h)
           echo "$0 -i <host_dhcp_interface> -t <docker_image_tag>"
	   exit 1
           ;;
        i)
           host_dhcp_interface=$OPTARG
	   /;;
        t)
           docker_tag=$OPTARG
	   ;;
        p)
           host_port=$OPTARG
           ;;
        *)
           echo "$0 -i <host_dhcp_interface> -t <docker_image_tag>"
	   exit 1
	   ;;
    esac
done	


log()
{
   echo -e ${PRX}"$(date "+%b %d %T") : $@" >> $LOG_FILE
}

log_and_exec()
{
   log "$@"
   eval "$@" 2>&1 |tee -a $LOG_FILE
}


# Prepare for docker environment
log_and_exec "rm $LOG_FILE"
log_and_exec "docker --version"
if [ $? -ne 0 ]; then
   log_and_exec "apt-get remove docker docker-engine"
   log_and_exec "apt-get update"
   log_and_exec "apt-get install -y apt-transport-https ca-certificates curl software-properties-common"
   log_and_exec "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -"
   log_and_exec "sudo apt-key fingerprint 0EBFCD88"
   log_and_exec "sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable""
   log_and_exec "apt-get update"
   log_and_exec "apt-get install -y docker-ce"
else
   echo "Docker already installed; Version: $(docker --version)"
fi

# Setup the host network
log_and_exec "apt-get install -y openvswitch-switch"
log_and_exec "ovs-vsctl add-br ovs-br0"
log_and_exec "ovs-vsctl add-port ovs-br0 $NETWORK"
log_and_exec "ip link set dev ovs-br0 up"

# Setup docker container network
log_and_exec "docker images $DOCKER_IMG_NAME:$DOCKER_IMG_TAG"
log_and_exec "docker ps -a |grep -w $NAME"
if [ $? -ne 1 ]; then
   log_and_exec "docker container stop $NAME"
   log_and_exec "docker container rm $NAME"
fi
log_and_exec "docker pull $DOCKER_IMG_NAME:$DOCKER_IMG_TAG"
log_and_exec "docker ps -a |grep $NAME"
if [ $? -ne 1 ]; then
   "docker container rm $NAME"
fi

# Clone pipework for network configuration
log_and_exec "docker run --privileged -p $PORT:5901 -dit --name $NAME $DOCKER_IMG_NAME:$DOCKER_IMG_TAG /bin/bash"
log_and_exec "git config --global http.sslverify false"
log_and_exec "ls |grep pipework"
if [ $? -ne 0 ]; then
  log_and_exec "git clone https://github.com/jpetazzo/pipework.git"
  log_and_exec "scp $PWD/pipework/pipework /usr/local/bin/pipework"
  log_and_exec "chmod +x /usr/local/bin/pipework"
else
  echo "pipework is existing...."
fi
log_and_exec "/bin/bash $PWD/pipework/pipework ovs-br0 -i eth1 $NAME dhclient"
log_and_exec "docker exec $NAME brctl addbr br0"
log_and_exec "docker exec $NAME brctl addif br0 eth1"
log_and_exec "IP=$(docker exec $NAME ifconfig eth1 | awk '/inet addr/{print substr($2,6)}')"
if [ $? -ne 0 ]; then
   echo "No DHCP services, please check DHCP server."
else
   echo "$IP"
   log_and_exec "docker exec $NAME ifconfig br0 $IP"
   log_and_exec "docker exec $NAME ifconfig br0 0.0.0.0"
fi
log_and_exec "docker exec $NAME infrasim node start"
