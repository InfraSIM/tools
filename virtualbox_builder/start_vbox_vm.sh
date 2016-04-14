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

if [ ! -e ${target_name}.vdi ]; then
	echo "Can't find "${target_name}.vdi", please run ./virtualbox_builder.sh first"
	exit 1
fi

#clean up the existing VM
vboxmanage unregistervm "${target_name}" 2>/dev/null
rm -rf ~/VirtualBox\ VMs/${target_name}
[ -e disk2.vdi ]; rm -rf disk2.vdi

#start to create virtualbox VM
vboxmanage createvm --name "${target_name}" --register
vboxmanage modifyvm "${target_name}" --memory 1024 --acpi on --nic1 nat --nictype1 82540EM --ostype Linux_64
vboxmanage createhd --filename ./disk2.vdi --size 8092
vboxmanage storagectl "${target_name}" --name "IDE Controller" --add ide
vboxmanage storageattach "${target_name}" --storagectl "IDE Controller" --port 0 --device 0 --type hdd --medium ./vnode.vdi
vboxmanage storageattach "${target_name}" --storagectl "IDE Controller" --port 0 --device 1 --type hdd --medium ./disk2.vdi
vboxmanage storageattach "${target_name}" --storagectl "IDE Controller" --port 1 --device 0 --type dvddrive --medium emptydrive


vboxmanage startvm "${target_name}"
