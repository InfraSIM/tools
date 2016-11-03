#!/bin/bash
# modify bmc interface in box
sed -i "s/\(interface: \).*/\1enp0s8/g" /usr/local/infrasim/etc/infrasim.yml
