#!/usr/bin/env bash

set +x
set -o errexit
set -o nounset

die() {
    echo $1
    exit 1
}

usage() {
    echo "$0 [--package-type] [--source-path] [--pkgname] [--pkgversion] [--pkgrelease]"
    exit 0
}

CHECKINSTALL=`which checkinstall`
ARCH=x86_64
JOBS=32

[ -n "$CHECKINSTALL" ] || die "Please install checkinstall."

pkgrelease=1
src=""
while [ $# -gt 0 ]; do
    option=$1
    case $option in
    --package-type) type=$2;shift ;;
    --source-path) src=$2;shift ;;
    --pkgname) pkgname=$2;shift ;;
    --pkgversion) pkgversion=$2;shift ;;
    --pkgrelease) pkgrelease=$2;shift ;;
    --help) usage ;;
    esac

    shift
done

[ -n "$src" -a -d "$src" ] || die "source code repo doesn't exist."

[ -n "$pkgname" ] || die "--pkgname is required."
[ -n "$pkgversion" ] || die "--pkgversion is required."

pushd $src

[ -f Makefile ] && make distclean
autoreconf -i
./configure CFLAGS="-lrt -lpthread" --prefix=/ --with-tcl=no
make -j${JOBS}

$CHECKINSTALL -D -y \
    --install=no \
    --fstrans=no \
    --reset-uids=yes \
    --pkgname=$pkgname \
    --pkgversion=$pkgversion \
    --pkgrelease=$pkgrelease \
    --exclude="/home" \
    --maintainer="InfraSIM Team <infrasim@googlegroups.com>" \
    make install

popd
