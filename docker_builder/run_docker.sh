#!/bin/bash
#Start a docker process based on infrasim:[tag] image

while getopts "hn:t:" args;do
    case ${args} in
        h)
            echo "$0 -n <docker_process_name> -t <docker_image_tag>"
            exit 1
            ;;
        n)
            docker_name=$OPTARG
            ;;
        t)
            docker_tag=$OPTARG
            ;;
        *)
            echo "$0 -n <docker_process_name> -t <docker_image_tag>"
            exit 1
            ;;
    esac
done

if [ -z "$docker_name" ]; then
	echo "Please give a name for docker process"
	exit 1
fi

if [ -z "$docker_tag" ]; then
	echo "please set which image tag you want to use"
	exit 1
fi

existing_image=$(docker images infrasim:${docker_tag} | grep ${docker_tag})
if [ -z "$existing_image" ]; then
	echo "Your specified image (infrasim:${docker_tag}) is not exist!!"
	exit 1
fi;


start_docker() {
	existing_container=$(docker ps -a | grep ${docker_name} | cut -d' ' -f 1)
	if [ -z "$existing_container" ]; then
		container_id=$(docker run -i -d --privileged --name ${docker_name} --net=bridge  -v /dev:/dev infrasim:${docker_tag} /bin/sh)
	else
		container_id=$(docker start ${existing_container})
	fi
	docker exec -u root ${container_id} /usr/sbin/telnetd -l /bin/ash
	docker exec -u root ${container_id} /sbin/sshd -f /etc/ssh/sshd_config
	docker exec -u root ${container_id} /sbin/syslogd -f /etc/syslog.conf
	docker exec -u root ${container_id} /bin/ipmi_sim -c /etc/ipmi/vbmc_docker.conf -f /etc/ipmi/vbmc.emu -n &
	docker exec -u root ${container_id} /usr/bin/qemu-system-x86_64 -vnc :1 --enable-kvm -boot order=ncd,menu=off \
						-device sga -chardev socket,id=ipmi0,host=localhost,port=9002,reconnect=10 \
						-device isa-ipmi,chardev=ipmi0,interface=bt,irq=5 -device ich9-usb-ehci1 \
						-m 484 -cpu Haswell,+vmx -smp 1 -bios /etc/ipmi/bios.bin -device ahci,id=ahci0 \
						-device e1000,mac=52:54:BE:EF:15:6E -machine vmport=off &
}

start_docker
