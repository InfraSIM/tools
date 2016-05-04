#!/bin/sh

while getopts "hd:n:" args;do
    case ${args} in
        h)
            echo "$0 -d <source directory> [-n <target image name>]"
            exit 1
            ;;
        d)
            NODE_FILES_PATH=$OPTARG
            ;;
        n)
            target_name=$OPTARG
            ;;
        *)
            echo "$0 -d <source directory> [-n <target image name>]"
			exit 1
            ;;
    esac
done

who=`id -u`
if [ $who -ne 0 ];then
    echo "Please run the script with 'sudo'."
    exit 0
fi

if [ -z "$target_name" ]; then
	echo "Please input the target image name"
	exit 1
fi


IMAGE=${target_name}.img

if [ -z "$NODE_FILES_PATH" ];then
    echo "$0 -d <source directory> [-n <target image name>]"
    exit 1
fi

[ -z "$QEMU_IMAGE" ] && QEMU_IMAGE=`which qemu-img`
[ -z "$SYSLINUX" ] && SYSLINUX=`which syslinux`
[ -z "$MBR" ] && MBR=/usr/lib/syslinux/mbr.bin

if [ -z "$QEMU_IMAGE" -o -z "$SYSLINUX" ];then
    echo "Please install qemu or syslinux."
    exit 1
fi

KERN_VER=3.16.0

# Detach all loop devices
loop_devices=`find /sys/block -type l -name "loop*" -exec basename {} \;`
for ld in $loop_devices;do
    losetup -d /dev/$ld >/dev/null 2>&1 
done

# The bootable virtual disk size, default is 128M
#unit: M
SIZE=128
COUNT=$SIZE
dd if=/dev/zero of=$IMAGE bs=1M count=$COUNT > /dev/null 2>&1 

PARTED=`which parted`
if [ -z "$PARTED" ];then
    echo "Please install parted first."
    exit 1
fi

$PARTED -s $IMAGE mklabel msdos

$PARTED --align=none -s $IMAGE mkpart primary fat32 0 ${SIZE}M > /dev/null 2>&1 

$PARTED --align=none -s $IMAGE set 1 boot on > /dev/null 2>&1 

# Write mbr.bin to first sector
dd if=$MBR of=$IMAGE bs=512 count=1 conv=notrunc > /dev/null 2>&1 

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

losetup -o 512 $loop_dev $IMAGE  >/dev/null 2>&1

mkdosfs $loop_dev >/dev/null 2>&1

if [ $? -ne 0 ];then
    echo "format loop0 failed"
    exit 1
fi

MOUNT_POINT=/tmp/ramfs

if [ ! -d $MOUNT_POINT ];then
    mkdir -p $MOUNT_POINT
fi

echo "Mount $loop_dev to $MOUNT_POINT"
mount -t vfat $loop_dev $MOUNT_POINT

echo "Copy files (config, System.map, ramfs.lzma and vmlinuz) to $MOUNT_POINT"

# Copy configuration file
cp syslinux.cfg $MOUNT_POINT

if [ ! -f $NODE_FILES_PATH/config-$KERN_VER ] \
    || [ ! -f $NODE_FILES_PATH/System.map-$KERN_VER ] \
    || [ ! -f $NODE_FILES_PATH/ramfs.lzma ] \
    || [ ! -f $NODE_FILES_PATH/vmlinuz-$KERN_VER ] ;then
    umount -fl $MOUNT_POINT
    exit 1
fi

# Copy related file
cp $NODE_FILES_PATH/config-$KERN_VER $MOUNT_POINT/config
cp $NODE_FILES_PATH/System.map-$KERN_VER $MOUNT_POINT/System.map
cp $NODE_FILES_PATH/ramfs.lzma $MOUNT_POINT/ramfs.lzma
cp $NODE_FILES_PATH/vmlinuz-$KERN_VER $MOUNT_POINT/vmlinuz

if grep -qs $MOUNT_POINT /proc/mounts;then
    umount -fl $MOUNT_POINT
fi

losetup -d $loop_dev

sleep 1

$SYSLINUX --install --offset 512 $IMAGE >/dev/null 2>&1
if [ $? -ne 0 ];then
    echo "Install syslinux failed."
    exit 1
fi

VB_IMAGE=box/vnode.vmdk
DISK2_IMAGE=box/disk2.vmdk
[ -e $VB_IMAGE ]; rm -rf $VB_IMAGE
[ -e $DISK2_IMAGE ]; rm -rf $DISK2_IMAGE

$QEMU_IMAGE convert -O vmdk $IMAGE $VB_IMAGE
vboxmanage createhd --format VMDK --filename $DISK2_IMAGE --size 8092
chmod 666 $VB_IMAGE
chmod 666 $DISK2_IMAGE

cd box
tar -cf ../${target_name}.box *

#clean up the environment
rm -rf vnode.vmdk
rm -rf disk2.vmdk
rm -rf ../$IMAGE
