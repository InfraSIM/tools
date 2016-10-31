#!/bin/bash

filename="/etc/rc.local"

sed -i "/By default.*/ a echo 1 > \/sys\/module\/kvm\/parameters\/ignore_msrs" $filename
sed -i "/By default.*/ a ifconfig ens224 promisc\nifconfig ens256 promisc" $filename
