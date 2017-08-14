#!/bin/bash
# This file write a systemd configuration,
# then enable a default infrasim node to
# be started with system.
cat >> /etc/systemd/system/infrasim.service <<EOF
[Unit]
Description=InfraSIM Compute Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/infrasim node start
ExecStop=/usr/local/bin/infrasim node stop
ExecReload=/usr/local/bin/infrasim node restart
Restart=on-failure
Environment=HOME=/home/infrasim/
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target

EOF

systemctl enable infrasim

