Below are steps to build PCIE topology.

1. Compile pcie_topo.py

        sudo pyinstaller pcie_topo.py --add-data id_table.json:./ 
 
2. Compress 'pcie_topo' in ./dist 

        tar -cf pcie_topo.tar pcie_topo 

3. Run pcie_topo in the server which you want to collect PCIE topology, 
   will generate a 'topology.yml'
   
        tar -xf pcie_topo.tar
        cd pcie_topo
        sudo ./pcie_topo

4. Insert topology.yaml into a target yaml(default: infrasim.yml)

        ./insert_yaml.py -S topology.yml -T infrasim.yml -O output.yml -E networks pcie_topology
 
5. 'output.yml' can be used to start infrasim-compute.

