# Packer build templates

The templates and related scripts are used for [packer](https://www.packer.io/) to build images.
The installation of packer is available on [downloadlink](https://www.packer.io/downloads.html).

Currently the templates for virtualbox and vmware are available, both are based on **Ubuntu16.04 LTS**.

## To build virtualbox image

    git clone https://github.com/InfraSIM/tools.git
    cd tools/packer
    packer build infrasim-box.json

The output file is named infrasim-compute.box.

## To build vmware image

    git clone https://github.com/InfraSIM/tools.git
    cd tools/packer
    packer build infrasim-vmware.json
    ovftool vmware-infrasim/packer-vmware-iso.vmx infrasim-compute.ova

The output file is named infrasim-compute.ova.

## How to Deploy

### For vmware:
The OVA file can be deployed in ESXi host.

### For virtualbox:
1. make sure the Vagrantfile and box file are in the same folder.
2. vagrant box add --name infrasim-compute infrasim-compute.box (use --force option if you already added a previous version before).
3. vagrant up
4. vagrant ssh
