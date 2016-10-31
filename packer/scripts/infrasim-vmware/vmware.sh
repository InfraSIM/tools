#!/bin/bash

# Bail if we are not running inside VMWare.
#if [[ `facter virtual` != "vmware" ]]; then
#    exit 0
#fi

# Install the VMWare Tools from a linux ISO.
sudo apt-get -y install open-vm-tools
