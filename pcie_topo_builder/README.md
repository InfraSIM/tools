# Below are steps to build PCIE topology.

## Manual execute
### Compile pcie_topo.py

        sudo pyinstaller pcie_topo.py --add-data id_table.json:./ 
 
### Compress 'pcie_topo' in ./dist

        tar -cf pcie_topo.tar pcie_topo 

### Run pcie_topo in the server which you want to collect PCIE topology,will generate a 'topology.yml'
   
        tar -xf pcie_topo.tar
        cd pcie_topo
        sudo ./pcie_topo

### Insert topology.yaml into a target yaml(default: infrasim.yml)

        ./insert_yaml.py -S topology.yml -T infrasim.yml -O output.yml -E networks pcie_topology
 
### 'output.yml' can be used to start infrasim-compute.

## Automation execute

        sudo ./run.py -J <jump_ip>:<jump_user>:<jump_pw> -S <server_ip>:<server_user>:<server_pw> -E <elements>

        eg.
            if you want to insert networks and pcie_topology node from source yaml file:
                networks:
                    - addr: '00.0'
                      bus: bus_01
                      device: e1000
                    - addr: '00.1'
                      bus: bus_01
                      device: e1000
                pcie_topology:
                    root_port:
                    - addr: '6.0'
                      bus: pcie.0
                      device: ioh3420
                      slot: 3

        you can config <elements> as networks and pcie_topology:
        sudo ./run.py -J <jump_ip>:<jump_user>:<jump_pw> -S <server_ip>:<server_user>:<server_pw> -E networks pcie_topology
