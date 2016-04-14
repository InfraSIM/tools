#!/usr/bin/env bash

set -e 

exit_function()
{
    echo "Exit and Cleanup."
    if grep -qs "$MOUNT_POINT" /proc/mounts;then
        umount -fl $MOUNT_POINT
    fi

    [ -d $ROOTFS ] && rm -rf $ROOTFS 

    [ -d $MOUNT_POINT ] && rm -rf $MOUNT_POINT

    if losetup -a | grep -qs "$loop_dev";then
        losetup -d $loop_dev
    fi

    [ -d $IMAGE_FOLDER ] && rm -rf $IMAGE_FOLDER

    lockfile-remove /var/lock/$loop_device_name
}

while getopts "hq:s:d:t:m:" args;do
    case ${args} in
        h)
            echo "$0 [ -q ] [ -e ] -d <source directory> [-t <target output file>]"
            exit 1
            ;;
        q)
            QEMU_IMAGE=$OPTARG
            ;;
        e)
            EXTLINUX=$OPTARG
            ;;
        d)
            NODE_FILES_PATH=$OPTARG
            ;;
        t)
            target_ova=$OPTARG
            ;;
        *)
            echo "$0 [ -q ] [ -s ] -d <source directory> [-t <target output file>]"
            exit 1
            ;;
    esac
done

# initialize exit function
trap exit_function EXIT

who=`id -u`
if [ $who -ne 0 ];then
    echo "Please run the script with 'sudo'."
    exit 0
fi

if [ -z "$NODE_FILES_PATH" ];then
    echo "$0 [ -q ] [ -s ] -d <source directory> [-t <target output file>]"
    exit 1
fi

# Convert relative path to absolute path
NODE_FILES_PATH=$(cd $NODE_FILES_PATH;pwd)

[ -z "$QEMU_IMAGE" ] && QEMU_IMAGE=`which qemu-img`
[ -z "$EXTLINUX" ] && EXTLINUX=`which extlinux`

if [ -z "$QEMU_IMAGE" -o -z "$EXTLINUX" ];then
    echo "Please install qemu or syslinux."
    exit 1
fi

if ! cat /proc/devices | grep -qs "loop"; then
    echo "Load loop driver"
    modprobe loop
fi

PARTED=`which parted`
if [ -z "$PARTED" ];then
    echo "Please install parted first."
    exit 1
fi

BUILDER_ROOT=$(cd $(dirname $0);pwd)
SIZE=256
KERN_VER=3.16.0
IMAGE=boot.img
NODE_TYPE=`basename $NODE_FILES_PATH`
VMDK=boot.vmdk
if [ -z "$target_ova" ];then
    target_ova=$NODE_TYPE.ova
fi

TEMPLATE=infrasim-${NODE_TYPE}-$(date +%H%M%S)
IMAGE_FOLDER=$(mktemp -d --tmpdir=$BUILDER_ROOT ${TEMPLATE}.XXXXXXXX)

pushd $IMAGE_FOLDER

# virtual disk size
dd if=/dev/zero of=$IMAGE bs=1M count=$SIZE > /dev/null 2>&1 

# dd if=/usr/lib/syslinux/mbr.bin of=$IMAGE bs=512 count=1 conv=notrunc > /dev/null 2>&1
$PARTED -s $IMAGE mklabel gpt
$PARTED --align=none -s $IMAGE mkpart primary ext3 0 ${SIZE}M #> /dev/null 2>&1 

#
# find first available loop device
#
loop_dev=""
loop_device_name=""
while true
do
    loop_dev=`losetup -f`
    [ -z "$loop_dev" ] && exit 1

    loop_device_name=${loop_dev##*/}
    lockfile-check -p /var/lock/${loop_device_name} || break
done

# Add a lock for each loop device
lockfile-create -p /var/lock/$loop_device_name

losetup $loop_dev $IMAGE  #>/dev/null 2>&1
mkfs.ext3 $loop_dev

MOUNT_POINT=$(mktemp -d --tmpdir=/tmp infrasim.XXXXXXXXXX)

echo "Mount $loop_dev to $MOUNT_POINT"
mount -t ext3 $loop_dev $MOUNT_POINT

#
# generate temp diretory to decompress ramfs
#
ROOTFS=$(mktemp -d --tmpdir=/tmp infrasim.XXXXXXXXXX)
pushd $ROOTFS

mkdir rootfs

cp $NODE_FILES_PATH/ramfs.lzma .

lzma -d ramfs.lzma

pushd rootfs
cpio -idmv < ../ramfs  >/dev/null 2>&1
popd

cp -ra rootfs/*  $MOUNT_POINT/
popd

# Create files needed by extlinux
[ ! -d $MOUNT_POINT/boot/extlinux ] && mkdir -p $MOUNT_POINT/boot/extlinux
cp $NODE_FILES_PATH/config-$KERN_VER $MOUNT_POINT/boot/config 
cp $NODE_FILES_PATH/System.map-$KERN_VER $MOUNT_POINT/boot/System.map 
cp $NODE_FILES_PATH/vmlinuz-$KERN_VER $MOUNT_POINT/boot/vmlinuz 
[ ! -d ${MOUNT_POINT}/boot/extlinux ] && mkdir -p ${MOUNT_POINT}/boot/extlinux
cp $BUILDER_ROOT/extlinux.conf $MOUNT_POINT/boot/extlinux
cp $BUILDER_ROOT/boot.png $MOUNT_POINT/boot/extlinux
cp /usr/lib/syslinux/vesamenu.c32 $MOUNT_POINT/boot/extlinux

$EXTLINUX -i $MOUNT_POINT/boot/extlinux

if grep -qs $MOUNT_POINT /proc/mounts;then
    umount -fl $MOUNT_POINT
fi

# detach loop device
# losetup -d $loop_dev

# clean temp files
# rm -rf $ROOTFS $MOUNT_POINT

###################################################
#
#   Create VMDK
#
###################################################

cp -r ../vmx .

echo "Creating vmdk $VMDK"
$QEMU_IMAGE convert -O vmdk $IMAGE $VMDK

mv $VMDK vmx/

if [ "$NODE_TYPE" = "hawk" -o "$NODE_TYPE" = "sentry" ];then
    sed -i "s/^\(displayName = \).*/\1\"$NODE_TYPE\"/g" vmx/vpdu.vmx
    ovftool --compress vmx/vpdu.vmx $target_ova
else

    VIRTUAL_DISK_SIZE=8 #unit: Gigabyte

    #Create two disks
    for i in $(seq 1 2);do
        virtual_disk=vmdisk${i}.vmdk
        if [ ! -f vmx/$virtual_disk ];then
            $QEMU_IMAGE create -f vmdk vmx/${virtual_disk} ${VIRTUAL_DISK_SIZE}G
        fi
    done

    sed -i "s/^\(displayName = \).*/\1\"$NODE_TYPE\"/g" vmx/vcompute.vmx
    ovftool --compress vmx/vcompute.vmx $target_ova
fi

mv $target_ova ..
popd

