# Infrasim-compute containerized
Which can make infrasim-compute run in a docker container.

## Dockerfile
Dockerfile is a text document that contains all the dependencies/commands a user
could call on the command line to assemble an infrasim-compute image. Using *docker build*
users can create an automated build that executes several command-line instructions.
Steps:
1. Copy the Dockerfile from the tools/docker directory into the infrasim-compute directory.
2. Run docker build command from infrasim-compute directory.

Command example:

    docker build -t infrasim-compute .

## docker.py
This script is used to manage infrasim-compute docker containers. It has 3 sub commands, start, stop and show.

**Note**: please set infrasim node "network_mode" to "bridge" and "network_name" to "br0"  in infrasim yml configuration.

The command of 'start' starts new infrasim nodes and the usage like,
    usage: docker.py start [-h] [-a] -i ETH -n NODES [NODES ...] [-l]

    optional arguments:
      -h, --help            show this help message and exit
      -a, --append          append new infrasim nodes
      -i ETH, --if ETH      network interface for bridge connection
      -n NODES [NODES ...], --nodes NODES [NODES ...]
                            node configuration, <yml_file,count>
      -l, --list            generate an IP list of containers after creation
                            done. 

This function helps you setup the docker running environment by,
 * pull an infrasim-compute image from docker hub if need,
 * Setup the container/host network to connect to a dhcp network interfaces. We leverage
 *OpenVswitch* and *pipework* to setup the dhcp network.
 * configure infrasim-compute and run it in a container
 * give an IP list of containers for remote access.
 
 
                            
The command of 'stop' stops infrasim nodes and clean up the environment.

    usage: docker.py stop [-h] [-i ETH]

    optional arguments:
      -h, --help        show this help message and exit
      -i ETH, --if ETH  the network interface
      
It stop all containers related to specified network interface and restore the network of host. 
If no eth is specifiled, it clean all containers.
                  
The command of 'show" gives an IP list of containers for remote access by SSH

    usage: docker.py show [-h] [-i ETH]

    optional arguments:
      -h, --help        show this help message and exit
      -i ETH, --if ETH  the network interface


Network connection as picture below:

![container_network](https://github.com/InfraSIM/tools/blob/master/docker/Infrasim-compute_container_network.jpg)

Command example:

        # Bring up 2 infrasim-compute in containers, start them by using specified cfg file and attach containers to the ethernet inferface of ens192,
        # give an IP list at the end.
        sudo ./docker.py start -i ens192 --nodes ./infrasim-node1.yml,2 -l

        # Teardown all infrasim containers and openvswitch attached to ens192 in the environment.
        sudo ./docker.py stop -i ens192

## Reference
 - https://docs.docker.com/
 - https://github.com/jpetazzo/pipework





