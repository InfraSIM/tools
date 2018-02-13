#!/bin/bash

export LC_ALL=C
#Install from apt sources
# install nvme-cli
#apt-get install python-software-properties -y
#add-apt-repository ppa:sbates << EOF
#
#EOF
#apt-get update
#apt-get install nvme-cli -y
#nvme list

git clone https://github.com/linux-nvme/nvme-cli.git
chown -R "`id -un`:`id -gn`" nvme-cli
cd nvme-cli
echo 'infrasim' | sudo -S make
echo 'infrasim' | sudo -S make install
sleep 1

# Test the nvme-cli code
echo 'infrasim' | sudo -S nvme list