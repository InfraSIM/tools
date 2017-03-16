## Vagrant files for vagrant-libvirt and vagrant-vaphere

An example Vagrantfile which can be used for @scale deployment with 
vSphere provider and Libvirt provider.

### Vagrant libvirt provider 
wiki page: 
https://github.com/InfraSIM/infrasim-compute/wiki/Vagrant-and-Libvirt-plugin-for-@scale-deployment

**Vagrant version: 1.9.2**

**vagrant-libvirt version: 0.0.37**

Command example:
    vagrant up --provider = libvirt
    vagrant ssh vagrant-1
    vagrant destroy
    vagrant up --provider = libvirt --debug &> vagrant.log
 	
### Vagrant vsphere provider
wiki page: 
https://github.com/InfraSIM/infrasim-compute/wiki/Vagrant-and-vSphere-plugin-for-@scale-deployment

**Vagrant version: 1.9.2**

**vagrant-vsphere version: 1.11.0**

Command example:

    vagrant up --provider = vsphere 
    vagrant ssh vagrant-1
    vagrant destroy
    vagrant up --provider = vsphere --debug &> vagrant.log
	
