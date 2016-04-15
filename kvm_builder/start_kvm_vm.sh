#!/bin/bash

while getopts "hn:" args;do
	case ${args} in
		h)
			echo "$0 -n <vm name>"
			exit 1
			;;
		n)
			target_name=$OPTARG
			;;
		*)
			echo "$0 -n <vm name>"
			exit 1
			;;
	esac
done

if [ -z "${target_name}" ]; then
	echo "$0 -n <vm name>"
	exit 1
fi

if [ ! -e "${target_name}.qcow2" ]; then
	echo "Can't find ${target_name}.qcow2, please run ./kvm_builder.sh first"
	exit 1
fi

#clean up the VM resource
virsh destroy ${target_name} 2>/dev/null
[ -e disk2.qcow2 ]; rm -rf disk2.qcow2
[ -e ${target_name}-kvm.xml ]; rm -rf ${target_name}-kvm.xml

#start the virt-manger VM
qemu-img create -f qcow2 disk2.qcow2 8G
python config/guest-parse.py config/guest.xml $(pwd) ${target_name}
virsh create ${target_name}-kvm.xml


