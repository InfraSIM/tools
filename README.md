The scripts in different folders are used to quickly build or manage the virtual compute node. Please see the detail introduction below.

Folders                | Description
--------               | ---
docker_builder         | Scripts to quickly build an compute node image on docker platform.
kvm_builder            | Script to quickly build an compute node image on KVM platform.
monorailtest           | Refer to the README.md in monorailtest folder.
ova_builder            | Script to quickly build an OVA image.
smbiostool             | Script to capture smbios data.
virtualbox_builder     | Script to quickly build an compute node image on virtual box platform.
vmworkstation_builder  | Script to quickly build an compute node image on vmworkstation platform.
vmx                    | Script to build an compute node image with vmx type. 
data_generater         | Script to generate the fru and sensor data for the new node simulation.
fru_data_parser        | Lib to read and write emu file, aka, ipmi\_sim\_cmd set. Can operate FRU data command in a human readable means now.
deb_builder            | Script to build deb package. 
