#!/bin/bash
sed -i "/By default.*/ a ifconfig enp0s9 promisc\nifconfig enp0s10 promisc" /etc/rc.local
