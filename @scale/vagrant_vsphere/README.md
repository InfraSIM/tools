# Vagrant and vSphere plugin for @scale deployment
## Introduction
"Vagrant - the command line utility for managing the life-cycle of virtual machines."
vagrant-vsphere - VMware vSphere provider for Vagrant, allowing Vagrant to control and provision machines using VMware 
vSphere. First, we can use vagrant to deployment InfraSIM @scale test environment on vCenter, VMs resources allocation will follow vSphere DRS (Distributed Resource Scheduler).
We can execute vagrant up, halt, reload, provision, destroy and ssh...command on VMs in parallel.

## Setup and Execution
### Vagrant and vSphere plugin setup
Here we select a VM with Ubuntu 16.04 installed as Vagrant host server.

* Vagrant host Environment Preparation: 

1. Install Vagrant dependency

	$ sudo apt-get install ruby-full
 
	$ sudo apt install ruby-bundler

	$ git clone https://github.com/mitchellh/vagrant.git

	$ cd vagrant

	$ bundle install

2. Install the latest version vagrant from https://www.vagrantup.com/downloads.html

	$ wget https://releases.hashicorp.com/vagrant/1.9.2/vagrant_1.9.2_x86_64.deb 

	$ sudo dpkg -i vagrant_1.9.2_x86_64.deb
	
	$ vagrant --version "to make sure Vagrant version as your expectation"

3. Install vagrant-vsphere plugin use standard vagrant plugin installation method.

	$ vagrant plugin install vagrant-vsphere

### The vagrant-vsphere box 
Which is hosted via Atlas in "InfraSIM/infrasim-compute" organization, we can define it in Vagrantfile.
https://atlas.hashicorp.com/InfraSIM/boxes/infrasim-compute

### Prepare for the **Vagrantfile** 
Prepare for "Vagrantfile" base on your exact test vCenter environment, an example "Vagrantfile" is uploaded to GitHub InfraSIM/tools/@scale/vagrant_vsphere/ repo for reference.
https://github.com/InfraSIM/tools

### Create a template/vm in vSphere/vCenter for vagrant proceed. 

Make sure the "template inventory location" and "template name" is the same as in **Vagrantfile**
![Clone a template in vCenter](https://github.com/chenge3/pics_for_wiki/blob/master/clone_to_template_in_vCenter.jpeg)

### You can also create a register vm through ESXi vim-cmd.
	
	$ vim-cmd solo/registervm /vmfs/volumes/datastore_name/VM_directory/VM_name.vm

### Create Customization Specifications through vSphere Center

This "spec" will be used when you need to set static IP for VM's "private network".
One key point, the NIC numbers in "spec" should match the NIC numbers in vm template.

![Create Customization Specification ](https://github.com/chenge3/pics_for_wiki/blob/master/Create_Customization_Specifications.jpeg)

### Run the vagrant command in Vagrant server to clone VMs in vCenter.
	
	$ vagrant up --provider=vsphere

### We can ssh to target VM
	
	$ vagrant ssh vagrant-1  

### We can delete all deployed VMs 

	$ vagrant destroy

### After all InfraSIM virtual nodes powered up, you can refer to Ansible playbook in InfraSIM/tools repo for further operation on InfraSIMs. 
https://github.com/InfraSIM/tools/pull/40

### Vagrant logs
If add "--debug" parameter we can save output to a file "vagrant.log". 

	$ vagrant up --debug &> vagrant.log

## Reference
1. https://www.vagrantup.com/docs/
2. https://github.com/mitchellh/vagrant
3. https://github.com/nsidc/vagrant-vsphere
4. https://pubs.vmware.com/vsphere-50/index.jsp?topic=%2Fcom.vmware.wssdk.pg.doc_50%2FPG_Ch13_Resources.15.6.html
5. https://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.vsphere.vm_admin.doc/GUID-70CD44B1-B27D-43E7-83D5-A76833B1CA8A.html
