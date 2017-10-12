#!/usr/bin/python

import os
import sys
import subprocess
import logging
import time
import re
import yaml
import argparse

global op

"""
This script will set up multiple infrasim node.
1. build docker environment,
2. build container
3. connect them through bridge,
4. start infrasim nodes.
"""


class DispatchingFormatter:
    def __init__(self, formatters, default_formatter):
        self._formatters = formatters
        self._default_formatter = default_formatter

    def format(self, record):
        formatter = self._formatters.get(record.name, self._default_formatter)
        return formatter.format(record)


class Operator():
    def init(self):
        # Docker log file location
        pwd = os.path.dirname(os.path.realpath(__file__))
        log_file = pwd + "/container_setup.log"

        # set the format for log file.
        file_format = DispatchingFormatter({
                'CMD': logging.Formatter(
                    '%(asctime)s:%(name)s:%(levelname)s:%(message)s'),
                'HINT': logging.Formatter('Script Hint: %(message)s'),
            },
            logging.Formatter("%(message)s"),
        )
        handler = logging.FileHandler(log_file, mode='a')
        handler.setFormatter(file_format)
        logging.getLogger().addHandler(handler)

        # set format for screen displaying.
        screen_format = DispatchingFormatter({
                'CMD': logging.Formatter(pwd + '$ %(message)s'),
                'HINT': logging.Formatter('HINT: %(message)s'),
            },
            logging.Formatter("%(message)s"),
        )

        handler = logging.StreamHandler()
        handler.setFormatter(screen_format)
        logging.getLogger().addHandler(handler)

        # set the logger level.
        logging.getLogger().setLevel(logging.DEBUG)

    def log_info(self, str):
        logging.getLogger('HINT').info(str)

    def log_err(self, str):
        logging.getLogger('CMD').error(str)

    def run(self, cmd="", shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE):
        """
        :param cmd: the command should run
        :param shell: if the type of cmd is string,
        :shell should be set as True, otherwise, False
        :param stdout: reference subprocess module
        :param stderr: reference subprocess module
        :return: tuple (return code, output)
        """
        logging.getLogger('CMD').info(cmd)
        child = subprocess.Popen(cmd, shell=shell, stdout=stdout,
                                 stderr=stderr)
        cmd_result = ""
        while True:
            output = child.stdout.readline()
            cmd_return_code = child.poll()
            if output == '' and cmd_return_code is not None:
                break
            if output:
                logging.getLogger('rsp').info(output.strip())
            cmd_result = cmd_result + output
        return cmd_return_code, cmd_result

    def perform(self, cmd=""):
        """
        perform the command without logging.
        """
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        cmd_return_code = child.returncode
        return cmd_return_code, cmd_result[0]


class Container:
    """
    The class handles the create/config container and start infrasim node.
    """
    def __init__(self, index, docker_image, bridge, cfg_file,
                 single_template=True):
        self._name = "container_{0}".format(index)
        self._port_name = "veth{0}".format(index)
        self._cfg = cfg_file
        self.__bridge = bridge
        node = cfg_file["name"]
        if node is None:
            node = "dell-r730"
        if single_template:
            self._node_name = "{0}-{1}".format(node, index)
        else:
            self._node_name = node

        self._docker_image = docker_image
        self._ip = None

    def start(self, index):
        ret = op.run("docker run -p {}:5901 --privileged -dit --name {} {}".
                     format(5901+index, self._name, self._docker_image))
        if ret[0] != 0:
            raise Exception("Fail to start container {0}".format(self._name))
        op.run("docker exec {} sudo service ssh start".format(self._name))

    def connect_network(self):
        op.run("pipework {2} -i eth1 -l {1} {0} "
               "dhclient".format(self._name, self._port_name, self.__bridge))

    def setup_inner_network(self):
        op.run("docker exec {0} sudo brctl addbr br0".format(self._name))
        op.run("docker exec {0} sudo brctl addif br0 eth1".format(self._name))
        ip = None
        net_mask = None
        # try 5 times to get available IP address from DHCP.
        retry_counter = 0
        while retry_counter < 5:
            time.sleep(1)
            ret = op.run("docker exec {0} sudo ifconfig eth1".format(self._name))
            m = re.search("inet addr:(\d+\.\d+\.\d+\.\d+).* "
                          "Mask:(\d+\.\d+\.\d+\.\d+)", ret[1])
            if m:
                ip = m.group(1)
                net_mask = m.group(2)
                break
            retry_counter += 1

        if (retry_counter >= 5):
            op.log_err("No DHCP service for {0}, please check DHCP server.".
                       format(self._name))
            raise Exception("No DHCP service available for container")

        print("IP={0}, MASK={1}".format(ip, net_mask))
        op.log_info("Assign {1} for eth1 on {0}".format(self._name, ip))
        op.run("docker exec {0} sudo ifconfig eth1 0.0.0.0".format(self._name))
        # connect br0 with gateway
        op.run("docker exec {2} sudo ifconfig br0 {0} netmask {1} up".
               format(ip, net_mask, self._name))
        self._ip = ip

    def __change_cfg(self):
        # reset some fields (net_mac, name, serial_socket) to default.
        self._cfg["name"] = self._node_name
        for net in self._cfg["compute"]["networks"]:
            if "mac" in net:
                net.pop("mac")
        if "serial_socket" in self._cfg:
            self._cfg.pop("serial_socket")

    def start_node(self):
        self.__change_cfg()
        # save / import cfg file and start node.
        with open('/tmp/cfg.yml', 'w') as outfile:
            yaml.dump(self._cfg, outfile, default_flow_style=False)
        op.run("docker cp /tmp/cfg.yml {0}:/home/infrasim/{1}.yml".
               format(self._name, self._node_name))
        op.run("docker exec {0} sudo infrasim config add default /home/infrasim/{1}.yml".
               format(self._name, self._node_name))
        op.run("docker exec {0} sudo infrasim config update default /home/infrasim/{1}.yml".
               format(self._name, self._node_name))
        op.run("docker exec {0} sudo infrasim node start".
               format(self._name))

    def display_ip_address():
        logging.getLogger('').info("{0}:{1}".format(self._name, self._ip))


class Host():
    """
    This class checks the condition of docker, pipework and eth.
    install packages if needs automatically.
    setup the network bridge for containers.

    it displays the IP address of all containers and nodes.
    it stop the containers and restore network as well.
    """
    def __init__(self, eth_name, append=False,
                 image="infrasim/infrasim-compute", tag="latest"):
        self.__eth = eth_name
        self.__docker_image = image
        self.__docker_image_tag = tag
        self.__start_index = 0
        self.__bridge = "ovs-br0"
        self.__append = append

    def pre_check(self):
        # check the network interface.
        ret = self.__get_ip_address(self.__eth)
        if ret is not None:
            ret = op.run("netstat -n | grep {0}:22".format(ret[0]))
            m = re.findall("ESTABLISHED", ret[1])
            if len(m) > 0:
                raise Exception("Interface {0} has SSH connection on it.".
                                format(self.__eth))

    def check_docker(self):
        ret = op.run("which docker")
        if (len(ret[1]) == 0):
            op.log_info("installing docker")
            op.run("apt-get remove docker docker-engine")
            op.run("apt-get update")
            op.run("apt-get install -y apt-transport-https ca-certificates "
                   "curl software-properties-common")
            op.run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg "
                   "| sudo apt-key add -")
            op.run("sudo apt-key fingerprint 0EBFCD88")
            op.run("sudo add-apt-repository \"deb [arch=amd64] "
                   "https://download.docker.com/linux/ubuntu "
                   "$(lsb_release -cs) stable\"")
            op.run("apt-get update")
            op.run("apt-get install -y docker-ce")
            ret = op.run("which docker")
            if (len(ret[1]) > 0):
                op.log_info("Successfully installed docker.")
            else:
                raise Exception("Failed to install docker, "
                                "please install it manually")
        else:
            op.log_info("Docker already installed; ")
            op.run("docker --version")

        # check image in local. pull it if not found.
        image = "{0}:{1}".format(self.__docker_image, self.__docker_image_tag)
        ret = op.run("docker images {0}".format(image))
        if (self.__docker_image not in ret[1]) or (
               self.__docker_image_tag not in ret[1]):
            ret = op.run("docker pull {0}".format(image))
            if (ret[0] != 0):
                raise Exception("Failed to pull {0}.".format(image))
        else:
            op.log_info("Image already exists")

    def check_vswitch(self):
        ret = op.run("which ovs-vsctl")
        if (len(ret[1]) == 0):
            op.run("apt-get install -y openvswitch-switch")

    def __get_ip_address(self, name):
        ret = op.perform("ifconfig {0}".format(name))
        m = re.search("inet addr:(\d+\.\d+\.\d+\.\d+).* "
                      "Mask:(\d+\.\d+\.\d+\.\d+)", ret[1])
        if m:
            ip = m.group(1)
            net_mask = m.group(2)
            return [ip, net_mask]

        return None

    def __create_new_bridge(self):
        # try find a unused bridge name
        index = 0
        while True:
            bridge_name = "ovs-br{0}".format(index)
            ret = op.run("ovs-vsctl br-exists {0}".format(bridge_name))
            if ret[0] == 2:
                self.__bridge = bridge_name
                op.run("ovs-vsctl add-br {0}".format(self.__bridge))
                break
            index = index + 1

    def create_vswitch(self):
        ret = op.run("ovs-vsctl iface-to-br {0}".format(self.__eth))
        if ret[0] == 0:
            # eth name is already connected to a bridge.
            if self.__append is False:
                raise Exception("The bridge is already used. Use stop first")
            else:
                self.__bridge == ret[1]
        else:
            self.__create_new_bridge()
            # set IP address of eth to bridge before attaching eth to bridge
            # otherwise it leads to dead lock.
            ret = self.__get_ip_address(self.__eth)
            if ret is None:
                raise Exception("No valid IP address for bridge")
            # erase IP address of Eth If first.
            op.run("ifconfig {0} 0.0.0.0".format(self.__eth))
            # enable promisc mode.
            op.run("ifconfig {0} promisc".format(self.__eth))
            # setup IP for bridge.
            op.run("ifconfig {0} {1} netmask {2} up".format(self.__bridge,
                                                            ret[0],
                                                            ret[1]))
            # connect Eth If with bridge.
            op.run("ovs-vsctl add-port {0} {1}".format(self.__bridge,
                                                       self.__eth))
            # power up bridge.
            op.run("ip link set dev {0} up".format(self.__bridge))

    def check_pipework(self):
        # Clone pipework for network configuration
        ret = op.run("which pipework")
        if (ret[0] != 0):
            op.run("git clone -c http.sslVerify=false "
                   "https://github.com/jpetazzo/pipework.git")
            op.run("cp $PWD/pipework/pipework /usr/local/bin/pipework")
            op.run("chmod +x /usr/local/bin/pipework")
        else:
            op.log_info("pipework already exists")

    def get_containers(self, cfg_list):
        containers = []
        # find the biggest value as start index for container name.
        running_containers = op.perform("docker ps -a")
        m = re.findall("\scontainer_(\d+)\s", running_containers[1])
        for item in m:
            if self.__start_index <= int(item):
                self.__start_index = int(item) + 1

        index = self.__start_index
        image = "{0}:{1}".format(self.__docker_image, self.__docker_image_tag)
        for cfg in cfg_list:
            with open(cfg["yml"]) as f:
                cfg_map = yaml.safe_load(f)
            for i in range(0, cfg["number"]):
                containers.append(Container(index, image,
                                            self.__bridge, cfg_map))
                index = index + 1

        return containers

    def setup_environment(self):
        self.pre_check()
        self.check_docker()
        self.check_vswitch()
        self.check_pipework()
        self.create_vswitch()

    def start_nodes(self, cfg_list):
        i = self.__start_index
        for container in self.get_containers(cfg_list):
            container.start(i)
            container.connect_network()
            container.setup_inner_network()
            container.start_node()
            i = i+1

    def show(self):
        if self.__eth:
            # get the bridge which links to specified eth
            ret = op.perform("ovs-vsctl iface-to-br {0}".format(self.__eth))
            if len(ret[1]) == 0:
                return
            bridge_name = ret[1]
            # get port (index) list which connects to the bridge
            ret = op.perform("ovs-vsctl list-ports {0}".format(bridge_name))
            m = re.findall("\s+veth(\d+)", ret[1])
        else:
            # get all containers (index) by "docker ps"
            ret = op.perform("docker ps -a")
            m = re.findall("\s+container_(\d+)", ret[1])

        # list IP address for the containers who uses the port (index)
        for container in m:
            container = "container_{0}".format(container)
            ret = op.perform("docker exec {0} sudo ifconfig br0".format(container))
            m2 = re.search("inet addr:(\d+\.\d+\.\d+\.\d+).* "
                           "Mask:(\d+\.\d+\.\d+\.\d+)", ret[1])
            if m2:
                print("==> {0}: {1}".format(container, m2.group(1)))

    def __clear_bridge(self, br):
        # iterate ports on this bridge.
        ret = op.perform("ovs-vsctl list-ports {0}".format(br))
        for eth in (ret[1].rstrip().split('\n')):
            op.run("ovs-vsctl del-port {0} {1}".format(br, eth))
            if eth.startswith("veth") is False:
                # if this is not "veth", it is a Eth If.
                op.run("ifconfig {0} -promisc".format(eth))
                op.run("dhclient {0}".format(eth))
            else:
                op.run("ifconfig {0} down".format(eth))
        # remove the useless bridge.
        op.run("ovs-vsctl del-br {0}".format(br))

    def stop(self, clean=False):
        bridges = []
        if self.__eth:
            # get the bridge which links to specified eth
            ret = op.perform("ovs-vsctl iface-to-br {0}".format(self.__eth))
            if len(ret[1]) == 0:
                return
            bridge_name = ret[1]
            bridges.append(bridge_name)
            # get port (index) list which connects to the bridge
            ret = op.perform("ovs-vsctl list-ports {0}".format(bridge_name))
            m = re.findall("\s+veth(\d+)", ret[1])
        else:
            # if not specify eth, close all.
            # get all containers (index) by "docker ps"
            ret = op.perform("docker ps -a")
            m = re.findall("\s+container_(\d+)", ret[1])
            # get all bridges.
            ret = op.perform("ovs-vsctl list-br")
            for bridge_name in ret[1].rstrip().split('\n'):
                bridges.append(bridge_name)

        for container in m:
            # stop container
            container = "container_{0}".format(container)
            op.run("docker container stop {}".format(container))
            if clean:
                op.run("docker container rm {}".format(container))

        # if clean is required, remove bridge and restore IP address
        if clean:
            for bridge_name in bridges:
                self.__clear_bridge(bridge_name)


class Args():
    node = None

    def __init__(self):
        self._parser = None
        self.build_parser()

    @staticmethod
    def file_number_pair(arg):
        val = arg.split(',')
        if len(val) != 2:
            raise argparse.ArgumentError(Args.node, "Node format error")

        if os.path.exists(val[0]) is False:
            raise argparse.ArgumentError(Args.node, "Can't find " + val[0])

        if int(val[1]) <= 0:
            raise argparse.ArgumentError(Args.node, "Count must greater "
                                         "than 0")
        ret = {}
        ret["yml"] = val[0]
        ret["number"] = int(val[1])
        return ret

    def build_parser(self):
        self._parser = argparse.ArgumentParser(
                        description="manage multiple containers "
                        "(using bridge mode) with infrasim node inside")
        sub_parsers = self._parser.add_subparsers(
                        dest='cmd',
                        description="start / stop / show nodes in container")

        start_cmd = sub_parsers.add_parser(
                        "start",
                        help="start multiple infrasim nodes in containers")
        start_cmd.add_argument(
                        '-a', '--append', action='store_true',
                        help='append new infrasim node', required=False)

        start_cmd.add_argument('-i', '--if', dest='eth', action='store',
                               required=True,
                               help='network interface for bridge connection')

        Args.node = start_cmd.add_argument('-n', '--nodes', nargs='+',
                                           required=True,
                                           type=Args.file_number_pair,
                                           help='node configuration, '
                                           '<yml_file,count>')

        start_cmd.add_argument('-l', '--list', action="store_true",
                               help='generate an IP list of containers after'
                               ' creation done.')

        show_cmd = sub_parsers.add_parser(
                                    "show",
                                    help="show information of infrasim nodes")
        show_cmd.add_argument('-i', '--if', dest='eth', action='store',
                              required=False, help='the network interface')

        stop_cmd = sub_parsers.add_parser(
                            "stop",
                            help="stop the containers created by this tool")

        stop_cmd.add_argument('-i', '--if', dest='eth', action='store',
                              required=False, help='the network interface')

    def parse_args(self):
        return self._parser.parse_args()


def main():
    global op
    op = Operator()
    parser = Args()
    args = parser.parse_args()

    if (os.geteuid() != 0):
            raise Exception("Please run as root!!")
    if args.cmd == "start":
        op.init()
        host = Host(args.eth, args.append)
        host.setup_environment()
        host.start_nodes(args.nodes)
        if args.list is True:
            host.show()

    elif args.cmd == "stop":
        op.init()
        host = Host(args.eth)
        host.stop(True)

    elif args.cmd == "show":
        host = Host(args.eth)
        host.show()

if (__name__ == "__main__"):
    try:
        main()
    except Exception as e:
        op.log_err(e)
        sys.exit(e)
