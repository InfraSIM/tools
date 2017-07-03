The scripts in different folders are used to quickly build or manage the virtual compute node. Please see the detail introduction below.

Folders                | Description
--------               | ---
ansibleplaybook        | Playbook of ansible tasks for infrasim installation and basic commands.
data_generater         | Script to generate the fru and sensor data for the new node simulation.
deb_builder            | Scripts to build openipmi and qemu deb packages.
diag_arp_flux          | Utility to fix ARP flux.
dmidecode-2.12         | Utility to collect smbios data.
docker                 | Contents to enable infrasim-compute to run in a docker container.
fru_data_parser        | Lib to read and write emu file, aka, ipmi\_sim\_cmd set. Enables to operate FRU data command in human readable means.
monorailtest           | Refer to the README.md in monorailtest folder.
packer                 | Templates and related scripts that used for packer to build images.
smbiostool             | Script to change attributes in smbios file.
@scale                 | Example Vagrantfile which can be used for @scale deployment with vSphere provider and Libvirt provider.
