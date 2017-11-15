#!/usr/bin/env bash

set +x
set -o errexit
set -o nounset

die() {
    echo $1
    exit 1
}

usage() {
    echo "$0 [--source-path] [--pkgname] [--pkgversion] [--build-number] [--pkgrelease]"
    exit 0
}

CHECKINSTALL=`which checkinstall`
ARCH=x86_64
JOBS=32

[ -n "$CHECKINSTALL" ] || die "Please install checkinstall."

src=""
while [ $# -gt 0 ]; do
    option=$1
    case $option in
    --source-path) src=$2;shift ;;
    --pkgname) pkgname=$2;shift ;;
    --pkgversion) pkgversion=$2;shift ;;
    --build-number) buildnumber=$2;shift;;
    --pkgrelease) pkgrelease=$2;shift ;;
    --help) usage ;;
    esac

    shift
done

[ -n "$src" -a -d "$src" ] || die "source code repo doesn't exist."

[ -n "$pkgname" ] || die "--pkgname is required."
[ -n "$pkgversion" ] || die "--pkgversion is required."


[ ! -d ${src}/build ] && mkdir -p ${src}/build
pushd $src/build

distribution=$(lsb_release -i | cut -d: -f2 | sed 's|^\s||g' | tr '[:upper:]' '[:lower:]')
os_dist_name=$(lsb_release -c | cut -d: -f2 | sed 's|^\s||g')

pkgversion=${pkgversion}-${distribution}-${os_dist_name}

#[ -f Makefile ] && make distclean
../configure --prefix=/usr/local --target-list=${ARCH}-linux-user,${ARCH}-softmmu \
    --disable-smartcard --disable-seccomp --disable-glusterfs --with-pkgversion="$pkgname ${distribution}-${os_dist_name} build-$buildnumber" --disable-tpm \
    --disable-vhdx --disable-bluez --disable-gtk --disable-cocoa --disable-sdl --disable-xen \
    --without-system-pixman
make -j${JOBS}

#sudo apt-get build-dep libxen-dev

$CHECKINSTALL -D -y \
    -d2 \
    --install=no \
    --fstrans=no \
    --deldoc=yes \
    --gzman=yes \
    --reset-uids=yes \
    --pkgname=$pkgname \
    --pkgversion=$pkgversion \
    --pkgrelease=$pkgrelease \
    --exclude="/home" \
    --maintainer="infrasim@googlegroups.com" \
    make install

popd
