# Vagrant and Libvirt plugin for @scale deployment

## Introduction
* "Vagrant - the command line utility for managing the life-cycle of virtual machines." (version: 1.9.2)
* Vagrant-libvirt plugin add a provider to Vagrant which allowing Vagrant to control and provision machines via libvirt toolkit. (version 1.3.1)
* Vagrant up, destroy, suspend, resume, halt, ssh, reload, package and provision commands.

# Setup and Execution

## Vagrant and libvirt setup
Here we select a VM with Ubuntu 16.04 installed as Vagrant host server.
* Vagrant host Environment Preparation: 
   
1.  Install Vagrant dependency

	$ sudo apt-get install ruby-full

	$ sudo apt install ruby-bundler

	$ git clone https://github.com/mitchellh/vagrant.git

	$ cd vagrant

	$ bundle install

2.  Install latest version vagrant from https://www.vagrantup.com/downloads.html
    
	$ wget https://releases.hashicorp.com/vagrant/1.9.2/vagrant_1.9.2_x86_64.deb 

	$ sudo dpkg -i vagrant_1.9.2_x86_64.deb

	$ vagrant --version  **"to make sure Vagrant version as your expectation"**

3.  Need to make sure your have all the build dependencies (in Ubuntu) installed for vagrant-libvirt. 

	**Uncomment all "deb-src" sources in "/etc/apt/sources.list"**

	$ sudo apt-get update

	$ sudo apt-get build-dep vagrant ruby-libvirt

	$ sudo apt-get install qemu libvirt-bin ebtables dnsmasq

	$ sudo apt-get install libxslt-dev libxml2-dev libvirt-dev zlib1g-dev ruby-dev

	$ sudo adduser $USER libvirtd

4.  Check the qemu version is not "infrasim-qemu".
	
	$ qemu-system-x86_64 --version

	- If the version is "QEMU emulator version infrasim-qemu_2.6.2-1.0.19ubuntu16.04, Copyright (c) 2003-2008 Fabrice Bellard",
	  run command first: **$ sudo dpkg -r infrasim-qemu**

	- If the version is "QEMU emulator version 2.5.0 (Debian 1:2.5+dfsg-5ubuntu10.9), Copyright (c) 2003-2008 Fabrice Bellard", 
	  go to install vagrant-libvirt plugin.
		

5.  Need to install vagrant-libvirt use standard vagrant plugin installation method.
    
	$ vagrant plugin install vagrant-libvirt

	$ vagrant plugin list

        vagrant-libvirt (0.0.37)

## Use "Packer" and Packer templates to build vagrant box.

   Packer build templates found in [ chef/bento github repo.](https://github.com/chef/bento).
    
	$ git clone https://github.com/chef/bento

	$ cd bento

	$ sudo packer build -only qemu -var "headless=true" ubuntu-14.04-amd64.json

	$ vagrant box add builds/ubuntu-14.04.libvirt.box --name "ubuntu1404"

	$ vagrant box list

	 ubuntu1404       (libvirt, 0)

  **While building your box using packer, ubuntu-14.04-amd64-libvirt-box is recommended.**
   
## Prepare Vagrantfile

   Prepare Vagrantfile for vagrant up, an example **"Vagrantfile"** is uploaded to GitHub InfraSIM/tools/@scale/vagrant_libvirt repo for reference.
   https://github.com/InfraSIM/tools

## Run the vagrant command in Vagrant host server to build VMs in Ubuntu.
    
	$ vagrant up --provider=libvirt

## Run Virsh command to get vm list

	$ virsh list

![virsh vm list](https://github.com/chenge3/pics_for_wiki/blob/master/virsh_vm_list.png)


## We can ssh to target VM

	$ vagrant ssh vagrant-1

## We can delete all deployed VMs 

	$ vagrant destroy

### After all InfraSIM virtual nodes powered up, you can refer to Ansible playbook in InfraSIM/tools repo for further operation on InfraSIMs. 
https://github.com/InfraSIM/tools/pull/40

### Vagrant logs
If add "--debug" parameter we can save output to a file "vagrant.log". 

	$ vagrant up --debug &> vagrant.log

### Check the vagrant-libvirt network status, this is used as vagrant management network to manage vm.
		
	$ virsh net-info vagrant-libvirt
	
	Name:           vagrant-libvirt
	UUID:           bce64e82-d217-45b2-ac7f-18a36e2dd516
	Active:         yes
	Persistent:     yes
	Autostart:      no
	Bridge:         virbr1

	$ ifconfig virbr1

	virbr1    Link encap:Ethernet  HWaddr 52:54:00:e7:b1:14  
          	  inet addr:192.168.121.1  Bcast:192.168.121.255  Mask:255.255.255.0
         	  UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
         	  RX packets:1118 errors:0 dropped:0 overruns:0 frame:0
	          TX packets:1024 errors:0 dropped:0 overruns:0 carrier:0
        	  collisions:0 txqueuelen:1000 
         	  RX bytes:156150 (156.1 KB)  TX bytes:180150 (180.1 KB)

# Reference
1. https://www.vagrantup.com/docs/
2. https://github.com/mitchellh/vagrant
3. https://github.com/vagrant-libvirt/vagrant-libvirt
4. https://linuxsimba.com/vagrant-libvirt-install
5. https://github.com/chef/bento
6. https://www.packer.io/docs/
