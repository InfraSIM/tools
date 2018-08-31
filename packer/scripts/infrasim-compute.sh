#!/bin/bash

export LC_ALL=C

# install dependency for infrasim-compute
rm /var/lib/dpkg/lock
apt-get install -y python-pip libssl-dev libpython-dev git bridge-utils libaio-dev

pip install setuptools
sleep 1

# install infrasim-compute
git clone https://github.com/InfraSIM/infrasim-compute.git
chown -R "`id -un`:`id -gn`" infrasim-compute
cd infrasim-compute
pip install -r requirements.txt
python setup.py install
sleep 1

# init infrasim service
infrasim init
wget https://raw.githubusercontent.com/InfraSIM/tools/master/packer/scripts/infrasim.yml -O ${HOME}/.infrasim/.node_map/default.yml -q
