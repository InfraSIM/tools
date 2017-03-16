#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import netifaces
    import json
    import subprocess
except ImportError, e:
    print e, ", do this first:"
    print ">> pip install {}".format(str(e).split()[-1])
    exit(1)


ROUTE_TABLE_PATH = "/etc/iproute2/rt_tables"
TABLE_PREFIX = "infrasim"
TABLES_TO_REMOVE = []
TABLES_TO_DEFINE = []
TABLE_USED_ID = []
BASE_TABLE_ID = 200

# dict_subnet can be in a form of
# {
#     "127.0.0.0/8": [
#         {
#             "if_name": "lo",
#             "ip": "127.0.0.1"
#         }
#     ],
#     "172.31.128.0/24": [
#         {
#             "if_name": "ens192",
#             "ip": "172.31.128.45"
#         },
#         {
#             "if_name": "br0",
#             "ip": "172.31.128.46"
#         }
#     ],
#     "192.168.128.0/18": [
#         {
#             "if_name": "ens160",
#             "ip": "192.168.133.183"
#         }
#     ]
# }
# if a subnet has more than two interface, it may be shorted by os
# and it goes to arp flux.
# In above example, subnet "172.31.128.0/24" needs fix.
dict_subnet = {}


def run_command(cmd="", shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    return cmd_return_code, cmd_result


class Interface(object):

    def __init__(self, ifname):
        self.name = ifname
        self.ifaddress = netifaces.ifaddresses(ifname)
        self.ifv4 = self.ifaddress.get(netifaces.AF_INET, [])

    def display(self):
        print "[{}]".format(self.name)
        print json.dumps(self.ifv4, indent=4)


# class SubNet(object):
#
#     def __init__(self, net, netmask):
#         self.net = net
#         self.netmask = netmask
#         self.ifs = {}
#
#     def register(self, new_if):
#         if new_if.name in self.ifs:
#             return
#         self.ifs[new_if.name] = new_if
#
#     def unregister(self, new_if):
#         del(self.ifs[new_if.name])


def update_arp_config():
    print "Set arp_ignore to 1: reply only if the target IP address " \
          "is local address configured on the incoming interface"
    cmd_arp_ignore = "echo 1 > /proc/sys/net/ipv4/conf/default/arp_ignore"
    ret, rsp = run_command('sh -c "{}"'.format(cmd_arp_ignore))
    if ret != 0:
        raise Exception("Fail to change arp_ignore to 1")
    else:
        print "    Done: {}".format(cmd_arp_ignore)

    print "Set arp_announce to 2: Always use the best local address for this target."
    cmd_arp_announce = "echo 2 > /proc/sys/net/ipv4/conf/default/arp_announce"
    ret, rsp = run_command('sh -c "{}"'.format(cmd_arp_announce))
    if ret != 0:
        raise Exception("Fail to change arp_announce to 2")
    else:
        print "    Done: {}".format(cmd_arp_announce)


def scan_specific_tables():
    """
    Scan /etc/iproute2/rt_tables, find all self defined route tables
    """
    global TABLES_TO_REMOVE
    with open(ROUTE_TABLE_PATH, "r") as fp:
        for line in fp.readlines():
            try:
                l = line.split()
                table_name = l[1].strip()
            except IndexError:
                continue
            if TABLE_PREFIX in table_name:
                TABLES_TO_REMOVE.append(table_name)


def define_infrasim_route_table():
    """
    Define a route table "infrasim<interface>" with available ID
    """
    global TABLES_TO_DEFINE
    global TABLE_USED_ID
    global BASE_TABLE_ID

    print "Define route table ..."

    for table in TABLES_TO_DEFINE:
        try:
            with open(ROUTE_TABLE_PATH, "a+") as fp:
                if table in fp.read():
                    print "Route table {} is defined in {}".\
                        format(table, ROUTE_TABLE_PATH)
                else:
                    # assign an ID
                    while BASE_TABLE_ID in TABLE_USED_ID:
                        BASE_TABLE_ID += 1
                    TABLE_USED_ID.append(BASE_TABLE_ID)
                    fp.write("{}\t{}\n".format(BASE_TABLE_ID, table))
                    print "    Route table {} (ID:{}) is written to {}".\
                        format(table, BASE_TABLE_ID, ROUTE_TABLE_PATH)
        except IOError, e:
            print "Fail to define {} route table: {}".format(table, e)
            exit(1)


def remove_specific_tables():
    global TABLE_USED_ID
    print "Remove pre-defined IP route table from {}".format(ROUTE_TABLE_PATH)
    with open(ROUTE_TABLE_PATH, "r+") as fp:
        lines = fp.readlines()
        fp.seek(0)
        for line in lines:
            found = False
            for table in TABLES_TO_REMOVE:
                if table in line:
                    found = True
                    break
            if found:
                print "    {} is removed".format(line.strip())
                continue
            else:
                fp.write(line)
                try:
                    TABLE_USED_ID.append(int(line.split()[0]))
                except ValueError:
                    continue
        fp.truncate()


def route_table_flush_infrasim(table):
    """
    Flush route table
    """
    print "Flush route table ..."
    ret, rsp = run_command("ip route flush table {}".format(table))
    if ret != 0:
        print "Fail to flush ip route table {}".format(table)
    else:
        print "    IP route table {} is flushed".format(table)


def get_subnet_in_str(str_ip, str_netmask):
    """
    Given two IP address in string, return subnet address in string
    :param str_ip: in a form of "192.168.128.100"
    :param str_netmask: in a form of "255.255.128.0", have to be a valid netmask
    :return: in a form of "192.168.128.0/17"
    """
    int_ip = ip_to_int(str_ip)
    int_netmask = ip_to_int(str_netmask)
    int_subnet = [x & y for x, y in zip(int_ip, int_netmask)]

    netmask_bit = 0
    mask_map = [0, 128, 192, 224, 240, 248, 252, 254, 255]
    for i in range(len(int_netmask)-1):
        if int_netmask[i] != 255:
            if int_netmask[i+1] != 0:
                raise Exception("Invalid netmask: {}".format(str_netmask))
    for mask in int_netmask:
        if mask not in mask_map:
            raise Exception("Invalid netmask: {}".format(str_netmask))
        else:
            netmask_bit += mask_map.index(mask)

    return "{}/{}".format(".".join([str(x) for x in int_subnet]), netmask_bit)


def ip_to_int(str_ip_address):
    """
    Get IPv4 address in string, return a list of ints
    """
    ip_in_str = str_ip_address.split(".")
    if len(ip_in_str) != 4:
        raise Exception("Invalid IPv4 address: {}".format(str_ip_address))
    ip_in_int = map(lambda x: int(x, 10), ip_in_str)
    for addr in ip_in_int:
        if addr < 0 or addr > 255:
            raise Exception("Invalid IPv4 address: {}".format(str_ip_address))
    return ip_in_int


def scan_all_interfaces():
    """
    Scan all addresses on all interfaces, then fill dict_subnet
    with subnet information
    """
    global dict_subnet
    global TABLES_TO_DEFINE
    TABLES_TO_DEFINE = []
    print "Scanning all interfaces..."
    ifs = netifaces.interfaces()
    for interface in ifs:
        obj_if = Interface(interface)

        if_name = obj_if.name
        for dict_ipv4 in obj_if.ifv4:
            try:
                if_addr = dict_ipv4["addr"]
                if_mask = dict_ipv4["netmask"]
            except KeyError, e:
                continue
            subnet = get_subnet_in_str(if_addr, if_mask)
            print "    {} ip:{} netmask:{} in subnet:{}".format(if_name, if_addr, if_mask, subnet)
            if subnet not in dict_subnet:
                dict_subnet[subnet] = []
            dict_subnet[subnet].append({"if_name": if_name, "ip": if_addr})

    print "Subnet statistics:"
    print json.dumps(dict_subnet, indent=4, sort_keys=True)

    subnet_ct = 0
    print "Subnets has arp flux risks:"
    for subnet in dict_subnet:
        if len(dict_subnet[subnet]) >= 2:
            subnet_ct += 1
            print "    {}".format(subnet)

            for info in dict_subnet[subnet]:
                table_name = "{}{}".format(TABLE_PREFIX, info["if_name"])
                if table_name not in TABLES_TO_DEFINE:
                    TABLES_TO_DEFINE.append(table_name)
    if subnet_ct == 0:
        print "    None"


def route_table_add_interface_rule():
    print "Add IP route rules for table {} ...".format(TABLE_PREFIX)
    for subnet in dict_subnet:
        if len(dict_subnet[subnet]) >= 2:
            # add rules
            # 1. ip rule add from <ip> table <table>
            # 2. ip route add <subnet> via <ip> dev <interface> table <table>
            for info in dict_subnet[subnet]:
                cmd_ip_rule = "ip rule add from {} table {}".format(info["ip"], TABLE_PREFIX+info["if_name"])
                ret, rsp = run_command(cmd_ip_rule)
                if ret != 0:
                    print "    Fail to run: {}".format(cmd_ip_rule)
                    exit(1)
                print "    {}".format(cmd_ip_rule)

                cmd_ip_route_on_nic = "ip route add {} via {} dev {} table {}".\
                    format(subnet, info["ip"], info["if_name"], TABLE_PREFIX+info["if_name"])
                ret, rsp = run_command(cmd_ip_route_on_nic)
                if ret != 0:
                    print "    Fail to run: {}".format(cmd_ip_route_on_nic)
                    exit(1)
                print "    {}".format(cmd_ip_route_on_nic)

                gateway = default_gateway(subnet)
                cmd_ip_route_default = "ip route add default via {} dev {} table {}".\
                    format(gateway, info["if_name"], TABLE_PREFIX+info["if_name"])
                ret, rsp = run_command(cmd_ip_route_default)
                if ret != 0:
                    print rsp
                    print "    Fail to run: {}".format(cmd_ip_route_default)
                    print "        Use a valid gateway address and run below command:"
                    print "        ip route add default via <gateway> dev {} table {}".\
                        format(info["if_name"], TABLE_PREFIX+info["if_name"])
                else:
                    print "    {}".format(cmd_ip_route_default)

        else:
            continue


def default_gateway(subnet):
    """
    Transfer a subnet string to a default gateway IP address: the first one in the subnet
    :param subnet: in a form of "192.168.128.0/24"
    :return: in a form of "192.168.128.1"
    """
    subnet_addr = subnet.split("/")[0]
    subnet_addr_in_int = ip_to_int(subnet_addr)
    subnet_addr_in_int[-1] |= 0x1
    return ".".join([str(x) for x in subnet_addr_in_int])


def route_flush_cache():
    cmd_flush_cache = "ip route flush cache"
    ret, rsp = run_command(cmd_flush_cache)
    if ret != 0:
        raise Exception("Fail to flush ip route cache")
    else:
        print "IP route flush cache is done"


if __name__ == "__main__":

    # gws = netifaces.gateways()
    # print gws['default'][netifaces.AF_INET]

    update_arp_config()

    # clean environment
    scan_specific_tables()
    for table in TABLES_TO_REMOVE:
        route_table_flush_infrasim(table)
    remove_specific_tables()

    # add new configuration
    scan_all_interfaces()
    define_infrasim_route_table()
    route_table_add_interface_rule()
    route_flush_cache()
