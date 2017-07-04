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
## docker.sh
The bash script includes below functions:
 * docker.sh can help you setup the docker running environment;
 * pull an infrasim-compute image from docker hub
 * run an infrasim-compute in a container
 * Setup the container/host network to connect to a dhcp network interfaces. We leverage
 *OpenVswitch* and *pipework* to setup the dhcp network.
 
Network connection as picture below:

![container_network](https://github.com/chenge3/pics_for_wiki/blob/master/Infrasim-compute_container_network.jpg)

Command example:

        sudo ./docker.sh


## Reference
 - https://docs.docker.com/
 - https://github.com/jpetazzo/pipework




