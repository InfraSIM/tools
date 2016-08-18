#!/bin/bash

export LC_ALL=C

# instal dependency for infrasim-compute
apt-get -y install socat ipmitool qemu openipmi python-pip libssl-dev libssh-dev libpython-dev libffi-dev sgabios 

pip install setuptools
pip install --upgrade pip
sleep 1

# install infrasim-compute
pip install infrasim-compute
sleep 1

# init infrasim service
infrasim-init
