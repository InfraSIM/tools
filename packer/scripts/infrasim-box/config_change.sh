#!/bin/bash
# modify bmc interface in box
sed -i "s/\(interface: \).*/\1enp0s8/g" ${HOME}/.infrasim/.node_map/default.yml
