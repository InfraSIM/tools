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
auto enp0s3
iface enp0s3 inet dhcp

auto enp0s8
iface enp0s8 inet dhcp

auto enp0s9
iface enp0s9 inet static
address 0.0.0.0

auto enp0s10
iface enp0s10 inet static
address 0.0.0.0

EOF
