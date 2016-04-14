#!/bin/sh
#We will create the docker images using "infrasim:<docker_image_tag>" label

while getopts "hd:t:" args;do
    case ${args} in
        h)
            echo "$0 -d <source directory> -t <docker_image_tag>"
            exit 1
            ;;
        d)
            node_path=$OPTARG
            ;;
        t)
            node_tag=$OPTARG
            ;;
        *)
            echo "$0 -d <source directory> -t <docker_image_tag>"
            exit 1
            ;;
    esac
done


if [ -z "$node_tag" ]; then
		echo "Please specify the docker image tag"
		exit 1
fi

LZMA_FILE=${node_path}/ramfs.lzma
if [ ! -e "$LZMA_FILE" ]; then
	echo "The source directory doesn't contain the vnode image"
	echo "Please check your source directory"
	exit 1
fi


################################################################
################start to build docker image procedure###########
################################################################
ROOT=$(pwd)

#clear up the existing data
if [ -d "${node_tag}" ]; then
	rm -rf ${node_tag}
fi

existing_image=$(docker images infrasim:${node_tag} | grep ${node_tag})
if [ ! -z "$existing_image" ]; then
	image_id=$(echo $existing_image | cut -d' ' -f3)
	docker rmi ${image_id}
fi;


#Build the docker image
mkdir ${node_tag}
cp ${LZMA_FILE} ./
unlzma -d -7 ramfs.lzma
cd ${node_tag}
cpio -idv < ../ramfs
tar --numeric-owner -cf- . | docker import - infrasim:${node_tag}


#clean up the build environment
rm -rf ${ROOT}/${node_tag}
rm -rf ${ROOT}/ramfs
