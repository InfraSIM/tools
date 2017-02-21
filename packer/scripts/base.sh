#!/bin/bash

perl -p -i -e 's#http://us.archive.ubuntu.com/ubuntu#http://mirror.rackspace.com/ubuntu#gi' /etc/apt/sources.list

# reduces package installs to bare mininums
cat <<EOAPT > /etc/apt/apt.conf
APT::Install-Recommends "0";
APT::Install-Suggests "0";
Acquire::Languages "none";
Acquire::GzipIndexes "true";
Acquire::CompressionTypes::Order:: "gz";
Dir::Cache::srcpkgcache "";
Dir::Cache::pkgcache "";
EOAPT

# Update the box
apt-get -y update >/dev/null
apt-get -y install facter linux-headers-$(uname -r) build-essential zlib1g-dev libssl-dev libreadline-gplv2-dev unzip >/dev/null

# Tweak sshd to prevent DNS resolution (speed up logins)
echo 'UseDNS no' >> /etc/ssh/sshd_config

# Remove 5s grub timeout to speed up booting
cat <<EOF > /etc/default/grub
# If you change this file, run 'update-grub' afterwards to update
# /boot/grub/grub.cfg.

GRUB_DEFAULT=0
GRUB_TIMEOUT=0
GRUB_DISTRIBUTOR=`lsb_release -i -s 2> /dev/null || echo Debian`
GRUB_CMDLINE_LINUX_DEFAULT="quiet"
GRUB_CMDLINE_LINUX="debian-installer=en_US"
EOF

update-grub

# In case your control/data network is not connected to a DHCP yet
# Here we set the waiting time to 10s to reduce boot time
sed -i "s/TimeoutStartSec.*/TimeoutStartSec=30s/g" /lib/systemd/system/networking.service
sed -i "s/^timeout .*/timeout 5;/g" /etc/dhcp/dhclient.conf

# add infrasim to have no password asked for sudo privilege
touch /etc/sudoers.d/infrasim
chmod 666 /etc/sudoers.d/infrasim
echo "infrasim ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/infrasim
chmod 644 /etc/sudoers.d/infrasim
