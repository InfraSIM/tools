#!/bin/bash

sed -i "s/\(By default.*\)/\1\necho 1 > \/sys\/module\/kvm\/parameters\/ignore_msrs/g" /etc/rc.local
