#!/usr/bin/env python

'''
*************************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*************************************************************
'''
# -*- encoding: utf-8 -*-

import os
import re
import yaml
import argparse
import json

def parse_args():
    description = "usage: Generate PCIE Topology"
    parser = argparse.ArgumentParser(description = description)

    help = "Network device."
    parser.add_argument('--nic_device', type=str, help=help, default='e1000')

    help = "Network mode."
    parser.add_argument('--network_mode', type=str, help=help, default='bridge')

    help = "Network name."
    parser.add_argument('--network_name', type=str, help=help, default='br0')

    args = parser.parse_args();
    return args


def find_pcie_device(id_list, pcie_dev_list):
    tmp_list = []
    for id in id_list:
        for dev in pcie_dev_list:
            if id in dev:
                tmp_list.append(dev.split(" ")[0])
    return tmp_list

def gen_nic_device_node(bdf_list):
    tmp_node_list = []

    # add multi function
    multi_mask = []
    for bdf in bdf_list:
        if int(bdf.split(':')[1].split('.')[1]):
            multi_mask.append(bdf)
            bdf_tmp = bdf[:-1] + '0'
            multi_mask.append(bdf_tmp)

    for bdf in bdf_list:
        tmp_dict = {}
        tmp_dict['bus'] = "bus_{}".format(bdf.split(":")[0])
        tmp_dict['addr'] = "{}".format(bdf.split(":")[1])
        if bdf in multi_mask:
            tmp_dict['multifunction'] = 'on'
        tmp_node_list.append(tmp_dict)

    return tmp_node_list

def add_key(dict_key, target_list):
    re_list = []
    for tl in target_list:
        tmp_dict = {}
        tmp_dict = dict(tl.items() + dict_key.items())
        re_list.append(tmp_dict)
    return re_list

def gen_bridge_node(bdf_list):
    tmp_bridge_list = []
    for bdf in bdf_list:
        bridge_info = os.popen("lspci -vv -s {}".format(bdf))
        bridge_info = bridge_info.read()
        if "PCI bridge" not in bridge_info:
            continue
        [bus, devfn] = bdf.split(":")
        tmp_dict = {}
        tmp_dict['bus'] = "bus_{}".format(bus)
        tmp_dict['addr'] = "{}".format(devfn)
        tmp_dict['addr'] = str(tmp_dict['addr'])
        result = re.search( r"(secondary=)([a-zA-Z0-9]+),", bridge_info)
        sec_bus = result.group(2)
        tmp_dict['id'] = "bus_{}".format(sec_bus)
        result = re.search( r"(subordinate=)([a-zA-Z0-9]+),", bridge_info)
        sub_bus = result.group(2)

        if 'Upstream Port' in bridge_info:
            tmp_dict['port'] = 'Upstream'
            tmp_dict['device'] = 'x3130-upstream'
            tmp_bridge_list.append(tmp_dict)
            continue

        if 'Downstream Port' in bridge_info:
            tmp_dict['port'] = 'Downstream'
            tmp_dict['device'] = 'xio3130-downstream'
            tmp_dict['pri_bus'] = int(bus, 16)
        elif 'Root Port' in bridge_info:
            tmp_dict['bus'] = "pcie.0" # only for root
            tmp_dict['port'] = 'Root Port'
            tmp_dict['device'] = 'ioh3420'
            tmp_dict['pri_bus'] = 0
            tmp_dict['sub_bus'] = int(sub_bus, 16)

        result = re.search( r"(Slot #)(\d+)", bridge_info)
        if result:
            tmp_dict['slot'] = int(result.group(2))
        else:
            tmp_dict['slot'] = 0
        tmp_dict['sec_bus'] = int(sec_bus, 16)
        tmp_dict['chassis'] = 0
        tmp_bridge_list.append(tmp_dict)

    return tmp_bridge_list

def pick_list(key, target_list):
    re_list = []
    for li in target_list:
        if li['port'] == key:
            re_list.append(li)
    return re_list

def remove_key(key, target_list):
    for li in target_list:
        if key in li:
            li.pop(key)

def gen_nvme_size(nvme_device):
    size_str = os.popen("sg_readcap /dev/{}".format(nvme_device))
    size_str_2 = size_str.read()
    size_gr = re.search(r'Device size: (\d+) bytes', size_str_2)
    return int(size_gr.group(1))/1024/1024/1024



def gen_nvme_serial(nvme_device):
    serial_str = os.popen("sg_inq /dev/{}".format(nvme_device))
    serial_str_2 = serial_str.read()
    serial_gr = re.search(r'Unit serial number: ([a-zA-Z0-9]+)', serial_str_2)
    return serial_gr.group(1)

def gen_nvme_node(nvme_bdf_list):
    if not nvme_bdf_list:
        return []

    nvme_str = os.popen("ls /dev/nvme*")
    nvme_list = re.findall(r"(nvme\dn\d)", nvme_str.read())
    nvme_dict = {}
    bdf_nvme_list = []
    nvme_output_list = []

    for bdf in nvme_bdf_list:
        bdf_nvme_dict = {}
        bdf_1 = os.popen("find /sys/devices -name '*{}'".format(bdf))
        bdf_2 = bdf_1.read()
        bdf_3 = re.sub('\n', '', bdf_2)
        bdf_3 += '/nvme/nvme*'
        bdf_4 = os.popen("ls {}".format(bdf_3))
        bdf_5 = bdf_4.read()
        bdf_nvme_dict['search_result'] = bdf_5
        bdf_nvme_dict['bdf'] = bdf
        bdf_nvme_list.append(bdf_nvme_dict)

    for nvme in nvme_list:
        nvme_dict = {}
        nvme_dict['type'] = 'nvme'
        drive_list = []
        drive_dict = {}
        drive_dict['size'] = gen_nvme_size(nvme)
        drive_list.append(drive_dict)
        nvme_dict['drives'] = drive_list
        nvme_dict['serial'] = gen_nvme_serial(nvme)
        for bdf_str in bdf_nvme_list:
            if nvme in bdf_str['search_result']:
                nvme_dict['bus'] = "bus_" + bdf_str['bdf'].split(':')[0]
                nvme_dict['addr'] = bdf_str['bdf'].split(':')[1]
                break
        nvme_output_list.append(nvme_dict)
    return  nvme_output_list

def fix_root_port_addr(root_port_list, start_dev):
    # sort root port by key 'sec_bus' from low to high
    root_port_list.sort(key=lambda x: x['sec_bus'], reverse=False)
    # assign addr for root port
    tmp_dev = 0xff
    for rp in root_port_list:
        try:
            dev, func = str(rp['addr']).split('.')
        except Exception as e:
            raise e

        if int(func) == 0 or tmp_dev != dev:
            # is multifunction device
            start_dev += 1
        else:
            print "multifunction device !"
        rp['addr'] = "{}.{}".format(hex(start_dev)[2:], func)
        tmp_dev = dev
        print "assign addr {} to rootport {}".format(rp['addr'], rp['id'])

def add_multifunction_to_rootport(root_port_list):
    try:
        addr_list = [x['addr'].split('.')[0] for x in root_port_list if x['addr']]
        addr_set = set(addr_list)
        multi_addr = [x for x in addr_set if addr_list.count(x) != 1]
        for rp in root_port_list:
            if rp['addr'].split('.')[0] in multi_addr:
                rp['multifunction'] = 'on'
    except Exception as e:
        print "add_multifunction_to_rootport Failed!"
        raise e

def get_slot_list(source_list):
    slot_list = []
    for li in source_list:
        if 'slot' in li:
            slot_list.append(li['slot'])
    return slot_list

def fix_port_chassis(bridge_list):
    # assign chassis to root port
    root_port_list = [x for x in bridge_list
                      if x['port'] == 'Root Port']
    downstream_port = [x for x in bridge_list
                       if x['port'] == 'Downstream']
    chassis = 1;
    for rp in root_port_list:
        rp['chassis'] = chassis;
        for dp in downstream_port:
            if  rp['sec_bus'] <= dp['pri_bus'] <= rp['sub_bus']:
                dp['chassis'] = chassis
        chassis += 1;

def fix_port_slot(bridge_list):
    slot_list = get_slot_list(bridge_list)
    # replace slot with non-zero value
    slot = 1
    tmp_list = [x for x in bridge_list if 'slot' in x]
    for rp in tmp_list:
        if rp['slot'] == 0:
            while slot < 0xffff:
                if slot not in slot_list:
                    rp['slot'] = slot
                    print "assign slot {} to device {}".format(rp['slot'],
                                                               rp['id'])
                    slot_list.append(slot)
                    break
                slot += 1

'''
def remove_unused_root_port(bridge_node_list):
    rootport_inused = []
    found = 0
    rootport_node_list =  pick_list('Root Port', bridge_node_list)

    print rootport_node_list
    target_list = eth_node_list + nvme_node_list + pick_list('Upstream', bridge_node_list)

    for rp in rootport_node_list:
        for target in target_list:
            if rp['id'] == target['bus']:
                found = 1
                break;
        if found == 1:
            rootport_inused.append(rp)
            found = 0
'''

def main():
    print "==============================================="
    print "             pcie topology generate            "
    print "==============================================="
    args = parse_args()
    nic_dict_add = {}
    nic_dict_add['device'] = args.nic_device
    nic_dict_add['network_mode'] = args.network_mode
    nic_dict_add['network_name'] = args.network_name

    # generate id table
    try:
        with open('id_table.json') as f:
            id_dict = json.loads(f.read())
    except IOError as e:
        print "Failed to open file: id_table.json"
        return

    eth_id_list = id_dict['eth_id']
    nvme_id_list = id_dict['nvme_id']
    bridge_id_list = id_dict['bridge_id']

    pcie_dev = os.popen("lspci")
    pcie_dev_list = pcie_dev.read().split('\n')
    eth_bdf_list = find_pcie_device(eth_id_list, pcie_dev_list)
    nvme_bdf_list = find_pcie_device(nvme_id_list, pcie_dev_list)
    bridge_bdf_list = find_pcie_device(bridge_id_list, pcie_dev_list)

    # generate node from bdf
    eth_node_list = gen_nic_device_node(eth_bdf_list)
    nvme_node_list = gen_nvme_node(nvme_bdf_list)
    bridge_node_list = gen_bridge_node(bridge_bdf_list)

    # prepare networks
    network_dict = {}
    eth_node_list = add_key(nic_dict_add, eth_node_list)
    network_dict['networks'] = eth_node_list

    # prepare nvme in strage_backend
    if nvme_node_list:
        network_dict['storage_backend'] = nvme_node_list

    # prepare pcie_topology
    topo_dict = {}
    switch_dict = {}
    fix_port_chassis(bridge_node_list)
    ## fix slot problem for rootport
    fix_port_slot(bridge_node_list)
    ## pick upstream
    switch_dict['upstream'] = [x for x in bridge_node_list
                               if x['port'] == 'Upstream']
    ## pick downstream
    switch_dict['downstream'] = [x for x in bridge_node_list
                                 if x['port'] == 'Downstream']
    ## pick rootport
    topo_dict['root_port'] = [x for x in bridge_node_list
                              if x['port'] == 'Root Port']
    ## fix addr problem for rootport
    fix_root_port_addr(topo_dict['root_port'], 0x5)
    ## Add multifunction to rootport
    add_multifunction_to_rootport(topo_dict['root_port'])
    ## remove 'port' this will change upstream downstream rootport
    remove_key('port', bridge_node_list)
    remove_key('sub_bus', bridge_node_list)

    switch_list = []
    switch_list.append(switch_dict)
    topo_dict['switch'] = switch_list
    network_dict['pcie_topology'] = topo_dict

    with open('topology.yml', 'w') as f:
        yaml.dump(network_dict, f, default_flow_style=False)

    print "Done"


if __name__ == '__main__':
    main()
