# Vagrant and Libvirt plugin for @scale deployment

## Introduction
* "Vagrant - the command line utility for managing the life-cycle of virtual machines." (version: 1.9.2)
* Vagrant-libvirt plugin add a provider to Vagrant which allowing Vagrant to control and provision machines via libvirt toolkit. (version 1.3.1)
* Vagrant up, destroy, suspend, resume, halt, ssh, reload, package and provision commands.

# Setup and Execution

## Vagrant and libvirt plugin setup
Here we select a VM with Ubuntu 16.04 installed as Vagrant host server.
* Vagrant host Environment Preparation: 
   
1.  Install Vagrant dependency

    > $ sudo apt-get install ruby-full
 
    > $ sudo apt install ruby-bundler

    > $ git clone https://github.com/mitchellh/vagrant.git

    > $ cd vagrant

    > $ bundle install

2.  Install latest version vagrant from https://www.vagrantup.com/downloads.html

    > $ wget https://releases.hashicorp.com/vagrant/1.9.2/vagrant_1.9.2_x86_64.deb 

    > $ sudo dpkg -i vagrant_1.9.2_x86_64.deb

    > $ vagrant --version  **"to make sure Vagrant version as your expectation"**

3.  Need to make sure your have all the build dependencies (in Ubuntu) installed for vagrant-libvirt. 

**  Uncomment all "deb-src" sources in "/etc/apt/sources.list"**

    > $ sudo apt-get update

    > $ apt-get build-dep vagrant ruby-libvirt

    > $ sudo apt-get install qemu-kvm libvirt-bin libvirt-dev

    > $ sudo apt-get install qemu libvirt-bin ebtables dnsmasq

    > $ sudo apt-get install libxslt-dev libxml2-dev libvirt-dev zlib1g-dev ruby-dev

    > $ sudo adduser $USER libvirtd

4.  Need to install vagrant-libvirt use standard vagrant plugin installation method.

    > $ vagrant plugin install vagrant-libvirt

    > $ vagrant plugin list

    > vagrant-libvirt (0.0.37)

## Use "Packer" and Packer templates to build vagrant box.

   Packer build templates found in [ chef/bento github repo.](https://github.com/chef/bento).

> $ git clone https://github.com/chef/bento
> $ cd bento
> $ packer build -only qemu -var "headless=true" ubuntu-14.04.amd64.json
> $ vagrant box add builds/ubuntu-14.04.libvirt.box --name "InfraSIM"
> $ vagrant box list
> InfraSIM             (libvirt, 0)
> InfraSIM-Ubuntu-1604 (libvirt, 0)

**While building your box using packer, ubuntu-14.04-amd64-libvirt-box is recommended. **
   
## Prepare Vagrantfile
Please prepare this file base on provider info, an example is uploaded to GitHub InfraSIM/tools/@scale/vagrant_libvirt repo for reference.
https://github.com/InfraSIM/tools

## Run the vagrant command in Vagrant host server to build VMs in Ubuntu.
> $ vagrant up --provider=libvirt

## Run Virsh command to get vm list
> $ virsh list
 
 ![virsh vm list](https://github.com/chenge3/pics_for_wiki/blob/master/virsh_vm_list.png)


## We can ssh to target VM
> $ vagrant ssh vagrant-1

## We can delete all deployed VMs 
> $ vagrant destroy

### After all InfraSIM virtual nodes powered up, you can refer to Ansible playbook in InfraSIM/tools repo for further operation on InfraSIMs. 
https://github.com/InfraSIM/tools/pull/40

### Vagrant logs
If add "--debug" parameter we can save output to a file "vagrant.log". 
> $ vagrant up --debug &> vagrant.log

# Reference
https://www.vagrantup.com/docs/
 
https://github.com/mitchellh/vagrant

https://github.com/vagrant-libvirt/vagrant-libvirt

https://linuxsimba.com/vagrant-libvirt-install

https://github.com/chef/bento

https://www.packer.io/docs/
