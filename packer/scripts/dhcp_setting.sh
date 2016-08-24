#!/bin/bash

echo "cleaning up dhcp leases"
rm -f /var/lib/dhcp/*
echo "Base network interface config"
cat > /etc/network/interfaces << EOF
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto ens160
iface ens160 inet dhcp

auto ens192
iface ens192 inet dhcp

auto ens224
iface ens224 inet dhcp

auto ens256
iface ens256 inet dhcp

source /etc/network/interfaces.d/*.cfg
EOF
