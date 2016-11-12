#!/bin/bash

filename="/etc/rc.local"

sed -i "/By default.*/ a echo 1 > \/sys\/module\/kvm\/parameters\/ignore_msrs" $filename
