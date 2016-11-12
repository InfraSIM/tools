#!/bin/bash

cat > /etc/modprobe.d/kvm-intel.conf <<EOF
options kvm_intel nested=y
EOF
