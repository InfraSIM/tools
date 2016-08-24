#!/bin/bash

export LC_ALL=C

# instal dependency for infrasim-compute
apt-get install -y python-pip libssl-dev libpython-dev git

pip install setuptools
pip install --upgrade pip
sleep 1

# install infrasim-compute
git clone https://github.com/InfraSIM/infrasim-compute.git
cd infrasim-compute
pip install -r requirements.txt
python setup.py install
sleep 1

# init infrasim service
infrasim-init
