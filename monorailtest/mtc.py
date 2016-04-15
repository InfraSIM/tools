#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import sys
import os
sys.path.append(os.getcwd()+"/modules/pexpect-3.3")
sys.path.append(os.getcwd()+"/modules/texttable")
sys.path.append(os.getcwd()+"/modules/leasesparser")
import re
import json
import urllib2  #python 2.7
import xml.etree.ElementTree as et
import unicodedata
import getopt
from pprint import pprint
import subprocess
import httplib
from texttable import Texttable,get_color_string,bcolors
import pexpect
import threading
import stat
import ConfigParser
from leaseparser import *
import time
import logging
import logging.handlers
import code
import readline
import atexit
import cmd
import socket

NORMAL="\033[0m"
BLACK="\033[30m"
RED="\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
PEACHBLOW = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

global_node_list=[]
global_node_dhcp_info=[]
global_vm_list={}

bmc_mac_prefix="52:54:be:ef"

hosts = []
rackhd_server = ""

logger = None
format_dict = {
   1 : logging.Formatter('[%(asctime)s] - %(threadName)10s - %(levelname)5s - %(message)s'),
   2 : logging.Formatter('[%(asctime)s] - %(threadName)10s - %(levelname)5s - %(message)s'),
   3 : logging.Formatter('[%(asctime)s] - %(threadName)10s - %(levelname)5s - %(message)s'),
   4 : logging.Formatter('[%(asctime)s] - %(threadName)10s - %(levelname)5s - %(message)s'),
   5 : logging.Formatter('[%(asctime)s] - %(threadName)10s - %(levelname)5s - %(message)s')
}
class Logger():
    def __init__(self, logname, loglevel, logger):
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)

        #fh = logging.FileHandler(logname)
        fh = logging.handlers.RotatingFileHandler(logname, mode='a', maxBytes=10 * 1024 * 1024, \
                backupCount=10, encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        formatter = format_dict[int(loglevel)]
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

    def getlog(self):
        return self.logger


def read_single_keypress(msg):
    """Waits for a single keypress on stdin.

    This is a silly function to call if you need to do it a lot because it has
    to store stdin's current setup, setup stdin for reading single keystrokes
    then read the single keystroke then revert stdin back after reading the
    keystroke.

    Returns the character of the key that was pressed (zero on
    KeyboardInterrupt which can happen when a signal gets handled)

    """
    import termios, fcntl, sys, os
    fd = sys.stdin.fileno()
    # save old state
    flags_save = fcntl.fcntl(fd, fcntl.F_GETFL)
    attrs_save = termios.tcgetattr(fd)
    # make raw - the way to do this comes from the termios(3) man page.
    attrs = list(attrs_save) # copy the stored version to update
    # iflag
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK 
                  | termios.ISTRIP | termios.INLCR | termios. IGNCR 
                  | termios.ICRNL | termios.IXON )
    # oflag
    attrs[1] &= ~termios.OPOST
    # cflag
    attrs[2] &= ~(termios.CSIZE | termios. PARENB)
    attrs[2] |= termios.CS8
    # lflag
    attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                  | termios.ISIG | termios.IEXTEN)
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    # turn off non-blocking
    fcntl.fcntl(fd, fcntl.F_SETFL, flags_save & ~os.O_NONBLOCK)
    sys.stdout.write(msg)
    sys.stdout.flush()
    # read a single keystroke
    try:
        ret = sys.stdin.read(1) # returns a single character
    except KeyboardInterrupt: 
        ret = 0
    finally:
        # restore old state
        termios.tcsetattr(fd, termios.TCSAFLUSH, attrs_save)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags_save)
    return ret

def print_json(level, data, pause=True):
    if isinstance(data, dict):
       for key in data.keys():
           if isinstance(data[key], dict) or isinstance(data[key], list): 
              print CYAN + "    "*level + key + " : " + NORMAL
              level = level + 1
              print_json(level, data[key], pause)
              level = level - 1
              if pause:
                 read_single_keypress("")
           else:
              print GREEN + "    "*level + key + " : " + NORMAL + str(data[key])
    elif isinstance(data, list):
         for e in data:
            if isinstance(e, dict) or isinstance(e, list): 
               print_json(level, e, pause)
               print
            else:
               print "    "*level + str(e)



def get_node_id_re(prefix):
    if len(global_node_list) == 0:
        print RED + "No nodes in the list! Please run 'list' command!" + NORMAL
        return ""

    pattern = '^[0-9a-f]{0,20}' + prefix + '$'
    obj = re.compile(pattern)
    for node in global_node_list:
        match = obj.match(node['id'])
        if match:
           return match.group(0)
    return ""

def handle_get_request(url):
    onlog = logger.getlog()
    onlog.info("Executing API [GET]: " + url)
    time_start = time.time()
    request = urllib2.Request(url)
    response = None
    try:
        response = urllib2.urlopen(request, timeout=15)
        data = response.read()
        time_end = time.time()
        consumed = round(time_end - time_start, 3)
        onlog.info(str(response.getcode()) + " - " + url + " [ " + str(consumed) + "s ]")
        return (response.getcode(), data)
    except socket.timeout, e:
           onlog.error("Timeout [ " + url + " ]")
           return (404, "")
    except urllib2.HTTPError, e:
           onlog.error(str(e.code) + " - " + e.reason + "[ " + url + " ]")
           return (e.code, "")
    except urllib2.URLError, e:
           onlog.error(str(e.reason) + "[ " + url + " ]")
           return (503, "")
    else:
           onlog.error("Exception [ " + url + " ]")
           return (503, "")

def handle_post_request(url, post_data=None):
    onlog = logger.getlog()
    onlog.info("Executing API [POST]: " + url)
    time_start = time.time()
    if post_data:
        headers = {}
        headers['Content-Type'] = 'application/json'
        request = urllib2.Request(url, post_data, headers)
    else:
        request = urllib2.Request(url)
    request.get_method = lambda: 'POST'
    try:
           response = urllib2.urlopen(request, timeout=15)
           time_end = time.time()
           consumed = round(time_end - time_start, 3)
           onlog.info(str(response.getcode()) + " - " + url + " [ " + str(consumed) + "s ]")
           return (response.getcode(), response.read())
    except socket.timeout, e:
           onlog.error("Timeout [ " + url + " ]")
           return (404, "")
    except urllib2.HTTPError, e:
           onlog.error(str(e.code) + " - " + e.reason + "[ " + url + " ]")
           return (e.code, "")
    except urllib2.URLError, e:
           onlog.error("Service unavailable [ " + url + " ]")
           return (503, "")
    else:
           onlog.error("Exception [ " + url + " ]")
           return (503, "")

def handle_delete_request(url):
    onlog = logger.getlog()
    onlog.info("Executing API [DELETE]: " + url)
    time_start = time.time()
    request = urllib2.Request(url)
    request.get_method = lambda: 'DELETE'
    response = None
    try:
           response = urllib2.urlopen(request, timeout=15)
           time_end = time.time()
           consumed = round(time_end - time_start, 3)
           onlog.info(str(response.getcode()) + " - " + url + " [ " + str(consumed) + "s ]")
           return (response.getcode(), response.read())
    except socket.timeout, e:
           onlog.error("Timeout [ " + url + " ]")
           return (404, "")
    except urllib2.HTTPError, e:
           onlog.error(str(e.code) + " - " + e.reason + "[ " + url + " ]")
           return (e.code, "")
    except urllib2.URLError, e:
           onlog.error("Service unavailable [ " + url + " ]")
           return (503, "")
    else:
           onlog.error("Exception [ " + url + " ]")
           return (503, "")

def handle_put_request(url):
    pass

def handle_patch_request(url):
    pass

def monorail_skus_list(dump=True):
    api_url="http://" + rackhd_server + ":8080/api/1.1/skus"
    retcode, data = handle_get_request(api_url)
    if retcode != 200:
        return None

    sku_list = []
    if dump:
        table = Texttable()
        table.header(["sku id", "name"])
    jdata = json.loads(data)
    if isinstance(jdata, list):
        for d in jdata:
            if dump:
                table.add_row([d['id'], d['name']])
            sku_list.append({d['id']:d['name']})
    if dump:
        print table.draw()
    return sku_list

def monorail_skus_nodes_list(sku_id):
    api_url="http://" + rackhd_server + ":8080/api/1.1/skus/" + sku_id + "/nodes"
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
        return

    platform = ""
    sku_list = monorail_skus_list(False)
    for sku in sku_list:
        if sku.has_key(sku_id):
           platform = sku[sku_id]
           break

    table = Texttable()
    table.header(["name", "sku id", "node id"])
    jdata = json.loads(data)
    if isinstance(jdata, list):
        for d in jdata:
            table.add_row([platform, sku_id, d['id']])
    table_str = table.draw()
    print table_str
    dump_table_to_file(platform + "_skus.txt", table_str)

def monorail_config_get():
    api_url="http://" + rackhd_server + ":8080/api/1.1/config"
    retcode, data = handle_get_request(api_url)
    if retcode != 200:
       return
    rdata= json.loads(data)
    #print json.dumps(rdata, sort_keys=True, indent=4, separators=(',', ': '))
    print_json(0, rdata, False)
    return

def monorail_versions_get():
    api_url="http://" + rackhd_server + ":8080/api/1.1/versions"

    retcode, data = handle_get_request(api_url)
    if retcode != 200:
       return 
    rdata= json.loads(data)
    #print json.dumps(rdata, sort_keys=True, indent=4, separators=(',', ': '))
    table = Texttable()
    table.header(["package", "version"])
    if isinstance(rdata, list):
       for jd in rdata:
           #print jd['package'], jd['version']
           table.add_row([jd['package'], jd['version']])
       print table.draw()
    return

def monorail_node_obm_set(node_id, bmc_ip, bmc_user="admin", bmc_pass="admin"):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/obm"
    if bmc_ip == "":
       print "please specify your host ip."
       return

    json_dict = {"service":"ipmi-obm-service", "config": {"user":bmc_user, "password":bmc_pass, "host":bmc_ip}}
    #convert json str to json data type
    json_data = json.dumps(json_dict)
    handle_post_request(api_url, json_data)
    
def monorail_node_obm_get(node_id):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/obm"
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return
    jdata = json.loads(data)
    table = Texttable()
    table.header(["BMC IP", "User", "Password"])
    for jd in jdata:
        table.add_row([jd['config']['host'], jd['config']['user'], jd['config']['password']])
    print table.draw()

def monorail_workflows_library_get():
    api_url="http://" + rackhd_server + ":8080/api/1.1/workflows/library"

    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return
    json_data = json.loads(data)
    print "Avaiable workflows:"
    print "-------------------"
    for wf in list(json_data):
	print CYAN + wf['injectableName'] + NORMAL
        print "\ttasks:" 
        for t in wf['tasks']:
            if t.has_key('taskName'):
               print "\t   - " + t['taskName']
             
def monorail_workflowtasks_library():
    api_url = "http://" + rackhd_server + ":8080/api/1.1/workflows/tasks/library"
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return
    json_data = json.loads(data) 
    print GREEN + "Workflow tasks:" + NORMAL
    if isinstance(json_data, list):
       for d in json_data:
           print "\t" + d['injectableName']

def monorail_node_catalogs():
    api_url="http://" + rackhd_server + ":8080/api/1.1/catalogs"

    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return
    rdata= json.loads(data)
    #print json.dumps(rdata, sort_keys=True, indent=4, separators=(',', ': '))
    print_json(0, rdata, False)
    return

def monorail_node_catalogs_source(node_id, source, printed = True):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/catalogs/" + source
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return None
    rdata= json.loads(data, encoding="utf-8")
    if printed:
       print_json(0, rdata['data'])
    return rdata

def monorail_node_catalogs_id(node_id, dump = False):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/catalogs"

    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return
    rdata= json.loads(data, encoding="utf-8")
    if isinstance(rdata, list) and dump:
        for cdata in rdata:
            #if cdata['source'] == 'dmi':
            print_json(0, cdata['data'])
    return rdata

def monorail_node_workflows_active_get(node_id):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/workflows/active"
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return

    jdata = json.loads(data)
    print_json(0, jdata, False)

def monorail_node_workflows_active_delete(node_id):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/workflows/active"
    retcode, data = handle_delete_request(api_url)
    try:
        jdata = json.loads(data)
        print_json(0, jdata, False)
    except ValueError:
        print RED + "Decoding json has failed." + NORMAL

def monorail_node_workflows_get(node_id):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/workflows"
    retcode, data = handle_get_request(api_url)
    
    try:
        jdata = json.loads(data)
        print_json(0, jdata)
    except ValueError:
        print RED + "Decoding json has failed." + NORMAL
    
def monorail_node_workflow_set(node_id, action):
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/workflows?name=" + action
    print api_url
    retcode,data = handle_post_request(api_url)

    try:
        rdata= json.loads(data, encoding="utf-8")
        print_json(0, rdata, False)
    except ValueError:
        print RED + "Decoding json has failed." + NORMAL

    
def monorail_node_workflow_create():
    pass

def monorail_pollers_command_list(node_id):
    api_url = "http://" + rackhd_server + ":8080/api/1.1/nodes/" + node_id + "/pollers"
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return

    jdata = json.loads(data)
   
    print RED + "Poller commands: " + NORMAL
    if isinstance(jdata, list):
       for d in jdata:
           print CYAN + d['config']['command'] + NORMAL

def monorail_node_list():
    global global_node_list
    api_url="http://" + rackhd_server + ":8080/api/1.1/nodes"
    #print api_url

    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return -1
    #load = json.loads(data, encoding="utf-8")
    load = json.loads(data)
    nodes_list = list(load)
    #print list(load)
    
    if len(nodes_list) == 0:
        print RED + "No nodes found!" + NORMAL
        return -1

    #print nodes_list
    global_node_list[:] = []
    for node in nodes_list:

        if node['type'] == 'enclosure':
            continue

        if node['type'] == 'pdu':
            continue

        temp_node={}
        #print node['id'] + " | ",
        temp_node['id'] = node['id'];
        if node.has_key('sku'):
            temp_node['sku_id'] = node['sku'] 

        temp_identity=[]
        for identity in list(node['identifiers']):
           #print identity + " | ",
           temp_identity.append(identity)
	temp_node['identifier'] = temp_identity

        temp_node['obm'] = []
        if node.has_key('obmSettings'):
           node_obm_setting = list(node['obmSettings'])
           for nos in node_obm_setting:
               temp_obm = {}
               temp_obm['user'] = nos['config']['user']
               temp_obm['password'] = nos['config']['password']
               temp_obm['host'] = nos['config']['host']
               temp_node['obm'].append(temp_obm)
        #else:
        #    # Find the BMC info from catalogs and register it automatically
        #    bmc_ip = get_bmc_ip(node['id'])
        #    if bmc_ip != "":
        #       temp_obm = {}
        #       temp_obm['user'] = "admin" #default in vBMC
        #       temp_obm['password'] = "admin" #default in vBMC
        #       temp_obm['host'] = bmc_ip
        #       temp_node['obm'].append(temp_obm)
        #    
        #       # set the obm settings
        #       monorail_node_obm_set(node['id'], bmc_ip)

        #Get vm name for this node
        h,vmname = get_vmname_by_mac(node['identifiers'][0])
        if vmname != None:
            #temp_node['vmname'] = "{0}\n{1}".format(vmname, h)
            temp_node['vm'] = {'name':vmname, 'esxi':h}
        else:
            temp_node['vm'] = None

        global_node_list.append(temp_node)

    #print global_node_list
    global_node_list = sorted(global_node_list, key=lambda node: node['id'])
    return 0
 
def monorail_lookups_ip_get(identifier):
    api_url = "http://" + rackhd_server + ":8080/api/1.1" + "/" + "lookups?q=" + identifier
    retcode,data = handle_get_request(api_url)
    if retcode != 200:
       return "", "", ""
    
    load = json.loads(data)

    node_ip = ""
    mac_address = ""
    dhcp_id = ""
    if isinstance(load, list):
       if len(load) == 0:
           return "", "", ""
       for info in load:
           if (info.has_key('node') and info['node'] == identifier) \
              or (info.has_key('macAddress') and info['macAddress'] == identifier):
              if info.has_key('macAddress'):
                  mac_address = info['macAddress']
              if info.has_key('ipAddress'):
                  node_ip = info['ipAddress']
              if info.has_key('id'):
                  dhcp_id = info['id']
              break
    else:
       if load.has_key("macAddress"):
          mac_address = load['macAddress']
       if load.has_key('ipAddress'):
          node_ip = load['ipAddress']
       if load.has_key("id"):
          dhcp_id = info['id']
    return mac_address, node_ip, dhcp_id

def monorail_lookups_ip_delete(dhcp_id):
    api_url = "http://" + rackhd_server + ":8080/api/1.1" + "/lookups/" + dhcp_id
    return handle_delete_request(api_url)
    
def monorail_node_delete(node_id):
    api_url = "http://" + rackhd_server + ":8080/api/1.1" + "/nodes/" + node_id
    retcode,data = handle_delete_request(api_url)
    return retcode

def get_bmc_ip(node_id):
    '''Extract the bmc ip from catalogs'''
    catalog_data = monorail_node_catalogs_source(node_id, "bmc", False)
    if catalog_data and type(catalog_data) == dict:
        if catalog_data['node'] == node_id:
          return catalog_data['data']['IP Address']
    return ""

def delete_node_lookups(mac_addr):
    dhcp_id = get_dhcpid_by_mac(mac_addr)
    retcode,data = monorail_lookups_ip_delete(dhcp_id)
    if retcode != 200:
        return

    #remove dhcp info from global dhcp info list
    for ndi in global_node_dhcp_info:
        if ndi['id'] == dhcp_id:
            global_node_dhcp_info.remove(ndi)
            return

def delete_node(node_id):
    ret = monorail_node_delete(node_id)
    if ret != 200:
        return

    for node in global_node_list:
        if node['id'] == node_id:
            global_node_list.remove(node)

def delete_node_ip_list():
    while True:
        if len(global_node_dhcp_info) == 0:
            break
        ndi = global_node_dhcp_info.pop()
        monorail_lookups_ip_delete(ndi['id'])

def delete_node_list():
    if len(global_node_list) == 0:
        print RED + "No nodes in the list! Please run 'list' command!" + NORMAL
        return ""
    delete_node_ip_list()
    while True:
        if len(global_node_list) == 0:
            break
        node = global_node_list.pop()
        monorail_node_delete(node['id'])

def get_node_ip_list():
    if len(global_node_list) == 0:
       print RED + "No nodes in the list! Run 'list' command." + NORMAL
       return -1
    global_node_dhcp_info[:] = []
    for node in global_node_list:
        for identity in node['identifier']:
            ndi = {'mac':"",'ip':"---.---.---.---", "id":""}
            mac_address,ipaddr,dhcp_id = monorail_lookups_ip_get(identity)
            ndi['mac'] = identity
            ndi['ip'] = ipaddr
            ndi['id'] = dhcp_id 
            global_node_dhcp_info.append(ndi)
    return 0

def show_node_ip_list():
    table = Texttable()
    table.set_cols_align(['c', 'c', 'c', 'l'])
    table.set_cols_valign(['m', 'm', 'm', 'm'])
    table.set_cols_width([4, 24, 17, 15])
    table.header(["No.", "DHCP ID", "mac address", "ip address"])
    index = 0
    for ndi in global_node_dhcp_info:
        index=index+1
        table.add_row([str(index), ndi['id'], ndi['mac'], ndi['ip']])
    table_str = table.draw()
    print table_str
    onlog = logger.getlog()
    onlog.info("\n" + table_str)
    dump_table_to_file("node_ips.txt", table_str)

def show_node_list():
    if len(global_node_list) == 0:
       print RED + "No nodes in the list! Run 'list' command." + NORMAL
       return
    table = Texttable()
    table.set_cols_align(['c', 'c', 'l', 'l', 'c', 'c'])
    table.set_cols_valign(['m', 'm', 'm', 'm', 'm', 'm'])
    table.set_cols_width([3, 24, 35, 17, 32, 17])  
    #table.header([get_color_string(bcolors.BLUE, "No."), \
    #            get_color_string(bcolors.BLUE, "Node ID"), \
    #            get_color_string(bcolors.BLUE, "Compute Node"), \
    #            get_color_string(bcolors.BLUE, "BMC")])

    table.header(["No.", "Node ID","Compute Node", "BMC", "VM Name", "ESXi host"])
    index = 0
    for n in global_node_list:
	row = []
        index = index + 1
        row.append(str(index))
        row.append(n['id'])
        mac_ip = ""
	for mac in n['identifier']:
            ndi = get_ip_by_mac(mac)
            ip = ""
            if ndi != None:
               ip = ndi['ip']
            mac_ip = mac_ip + mac + " / " + ip + "\n"

        row.append(mac_ip)
        bmc_ip = ""
        username = ""
        password = ""
        if n.has_key('obm'):
            for o in n['obm']:
                bmc_ip = bmc_ip + o['host'] + '\n'
                #username = username + o['user'] + '\n'
                #password = password + o['password'] + '\n'
        #bmc_ip = bmc_ip + get_vmname_by_node_id(n['id']) + '\n' 
        row.append(bmc_ip)
        #row.append(username)
        #row.append(password)
        if n['vm'] != None:
            row.append(n['vm']['name'])
            row.append(n['vm']['esxi'])
        else:
            row.append(" ")
            row.append(" ")
        table.add_row(row)
    table_str = table.draw()
    print table_str
    onlog = logger.getlog()
    onlog.info("\n" + table_str)
    dump_table_to_file("nodes.txt", table_str)
    return

def show_node_list_without_bmc():
    if len(global_node_list) == 0:
        print RED + "No nodes in the list! Run 'list' command." + NORMAL
        return 0
    
    table = Texttable()
    table.set_cols_align(['c', 'c', 'c', 'c', 'c'])
    table.set_cols_valign(['m', 'm', 'm', 'm', 'm'])
    table.set_cols_width([3, 24, 35, 32, 17])  
    table.header([get_color_string(bcolors.BLUE, "No."), \
            get_color_string(bcolors.BLUE, "Node ID"), \
            get_color_string(bcolors.BLUE, "Compute Node"), \
            get_color_string(bcolors.BLUE, "VM Name"), \
            get_color_string(bcolors.BLUE, "ESXi host")])
    index = 0
    for n in global_node_list:
        if n.has_key('obm') and len(n['obm']) == 0:
            index = index + 1
            row = []
            row.append(get_color_string(bcolors.BLUE, str(index)))
            row.append(n['id'])
            mac_ip = ""
            for mac in n['identifier']:
                #find the ip
                ndi = get_ip_by_mac(mac)
                ip = ""
                if ndi:
                   ip = ndi['ip']
                mac_ip = mac_ip + mac + " / " + ip + "\n"
            row.append(mac_ip)
            if n['vm'] != None:
                row.append(n['vm']['name'])
                row.append(n['vm']['esxi'])
            else:
                row.append(" ")
                row.append(" ")
            table.add_row(row)
    table_str = table.draw()
    print table_str
    onlog = logger.getlog()
    onlog.info("\n" + table_str)
    dump_table_to_file("failed_nodes.txt", table_str)
    return  index

def get_dhcpid_by_mac(mac_addr):
    for ndi in global_node_dhcp_info:
        if ndi['mac'] == mac_addr:
           return ndi['id']

def get_ip_by_mac(mac_addr):
    for ndi in global_node_dhcp_info:
        if ndi['mac'] == mac_addr:
           return ndi
    return None

def get_mac_by_id(node_id):
    if len(global_node_list) == 0:
       print RED + "No nodes in the list! Run 'list' command." + NORMAL
       return
    for n in global_node_list:
        if n['id'] == node_id:
           #print n['identifier']
           return n['identifier']
    return []

####################################################
## Only worked for simulation envrionment
###################################################
def find_bmc_by_node_mac(bmc_mac_addr):
    bmc_mac_suffix = bmc_mac_addr[-5:]
    if len(global_node_list) == 0:
       print RED + "No nodes in the list! Run 'list' command." + NORMAL
       return
    for n in global_node_list:
        if n['identifier'][0][-5:] == bmc_mac_suffix and n['identifier'][0] != bmc_mac_addr:
           return n

def find_bmc_by_cn_mac(node_mac_addr):
    #get suffix
    mac_suffix = node_mac_addr[-5:]
    for ndi in global_node_dhcp_info:
        if ndi['mac'] != node_mac_addr and ndi['mac'][-5:] == mac_suffix:
           return ndi

def show_vbmc_and_vcompute_info():
    index = 0

    if len(global_node_list) == 0:
       print RED + "No nodes in the list! Run 'list' command." + NORMAL
       return

    print RED + "Attention: 'list matched' only works for vCompute and vBMC!" + NORMAL
    table = Texttable()
    table.set_cols_align(["c", "l", "l", "c"])
    table.set_cols_valign(["m", "m", "m", "m"])
    table.set_cols_width([3, 24, 35, 35])
    table.header(["No.", "Node ID", "vCompute Node(mac/ip)", "vBMC(mac/ip)"])

    temp_nodes_list = global_node_list
    for n in temp_nodes_list:
        format_str = ""
        if n['identifier'][0][0:11] != bmc_mac_prefix:
           continue

        row = []
        index = index + 1
        row.append(str(index))
        row.append(n['id'])

        mac_ip = ""
	for mac in n['identifier']:
            #find the ip
            ndi = get_ip_by_mac(mac)
            ip = "---.---.---.---"
            if ndi != None:
               ip = ndi['ip']
            mac_ip = mac_ip + mac + " / " + ip + "\n"

        row.append(mac_ip)

        #find bmc by node mac
        #nd = find_bmc_by_node_mac(n['identifier'][0])
        bmc_mac_ip = ""
        for mac in n['identifier']:
            ndi = find_bmc_by_cn_mac(mac)
            if ndi:
                bmc_mac_ip = bmc_mac_ip + ndi['mac'] + " / " + ndi['ip'] + "\n"
        row.append(bmc_mac_ip)
        table.add_row(row)
    print table.draw()
####################################END#############################################3

#@deprecated
def reboot_node(node_id):
    # find node mac address
    found = False
    for n in global_node_list:
        if n['id'] == node_id:
           found = True
           break
    if not found:
       print "Not found " + node_id
       return
    # find bmc mac address
    ndi = find_bmc_by_cn_mac(n['identifier'][0])  

    # find ip addr
    #print ndi['ip']

    cmd = "ipmitool -I lan -U admin -P password -H " + ndi['ip'] + " chassis power reset"
    print cmd
    res = os.popen(cmd)
    print res.read()
    # send ipmitool command
    #return_code = subprocess.Popen(cmd)
    #print "return code " + str(return_code)

#@deprecated
def power_off_node(node_id):
    # find node mac address
    found = False
    for n in global_node_list:
        if n['id'] == node_id:
           found = True
           break
    if not found:
       print "Not found " + node_id
       return
    # find bmc mac address
    ndi = find_bmc_by_cn_mac(n['identifier'][0])  

    # find ip addr
    #print ndi['ip']

    cmd = "ipmitool -I lan -U admin -P password -H " + ndi['ip'] + " chassis power off"
    print cmd
    res = os.popen(cmd)
    print res.read()
    # send ipmitool command
    #return_code = subprocess.Popen(cmd)
    #print "return code " + str(return_code)

#@deprecated
def power_on_node(node_id):
    # find node mac address
    found = False
    for n in global_node_list:
        if n['id'] == node_id:
           found = True
           break
    if not found:
       print "Not found " + node_id
       return
    # find bmc mac address
    ndi = find_bmc_by_cn_mac(n['identifier'][0])  

    # find ip addr
    #print ndi['ip']

    cmd = "ipmitool -I lan -U admin -P password -H " + ndi['ip'] + " chassis power on"
    print cmd
    res = os.popen(cmd)
    print res.read()
    # send ipmitool command
    #return_code = subprocess.Popen(cmd)
    #print "return code " + str(return_code)

#@deprecated
def power_status_node(node_id):
    # find node mac address
    found = False
    for n in global_node_list:
        if n['id'] == node_id:
           found = True
           break
    if not found:
       print "Not found " + node_id
       return
    # find bmc mac address
    ndi = find_bmc_by_cn_mac(n['identifier'][0])  

    # find ip addr
    #print ndi['ip']

    cmd = "ipmitool -I lan -U admin -P password -H " + ndi['ip'] + " chassis power status"
    print cmd
    res = os.popen(cmd)
    print res.read()
    # send ipmitool command
    #return_code = subprocess.Popen(cmd)
    #print "return code " + str(return_code)

def read_config(config_path, dump):
    global rackhd_server
    if not os.path.exists(config_path):
        print config_path + " not exists!"
        return False

    cf = ConfigParser.ConfigParser()
    cf.read(config_path)

    sections = cf.sections()

    if "RackHDServer" in sections:
        rackhd_server = cf.get("RackHDServer", "host")

    #clear hosts
    hosts[:] = []
    for s in sections:
        if s == "RackHDServer":
            continue
        else:
            hosts.append({"host":cf.get(s, "host"), \
                          "user":cf.get(s, "user"), \
                          "password":cf.get(s, "password")})
    if dump:
        table = Texttable()
        table.header(["No.", "section", "host", "user", "password"])
        index = 0
        for s in sections:
            index += 1
            if s == "RackHDServer":
                table.add_row([index, s, cf.get(s, "host"), "", ""])
            else:
                table.add_row([index, s, cf.get(s, "host"), cf.get(s, "user"), cf.get(s, "password")])
        table_str = table.draw()
        print table_str
        onlog = logger.getlog()
        onlog.info("\n" + table_str)
    return True

def update_option(config_path, section, option, value):
    cf = ConfigParser.ConfigParser()
    cf.read(config_path)
    if cf.has_section(section) and cf.has_option(section, option):
       cf.set(section, option, value)
       cf.write(open(config_path, "w"))
    else:
        print section + " is not in config file!"

def delete_section(config_path, section):
    cf = ConfigParser.ConfigParser()
    cf.read(config_path)
    #sections = cf.sections()
    if cf.has_section(section):
        cf.remove_section(section)
        cf.write(open(config_path, "w"))

def add_section(config_path, section, host, user, password):
    cf = ConfigParser.ConfigParser()
    cf.read(config_path)
    if cf.has_section(section):
        print section + " already exists!"
        return
    cf.add_section(section)
    cf.set(section, "host", host)
    cf.set(section, "user", user)
    cf.set(section, "password", password)
    cf.write(open(config_path, "w"))

def load_config(config_path):
    if not read_config(config_path, False):
        print "load config failed."
        return 

    send_and_execute_scripts()
    return

SSH_NEWKEY = r'Are you sure you want to continue connecting \(yes/no\)\?'
def execute_shell_cmd(host, user, password, cmd, sudo=False):
    onlog = logger.getlog()
    r = ""
    ssh_cmd = 'ssh ' + user + '@' + host + ' -t' + ' ' + cmd
    onlog.info("Running shell command: " + ssh_cmd)
    #print ssh_cmd
    ssh = pexpect.spawn("/bin/bash", ['-c', ssh_cmd])
    i = ssh.expect(['[Pp]assword:', SSH_NEWKEY, pexpect.EOF, pexpect.TIMEOUT])
    #print i
    if i == 0:
       ssh.sendline(password)
       if sudo:
           ssh.expect(["password for"])
           ssh.sendline(password)
       ssh.expect(pexpect.EOF, timeout=300)
       r = ssh.before
    elif i == 1:
       ssh.sendline('yes')
       ssh.expect('[Pp]assword:')
       ssh.sendline(password)
       if sudo:
           ssh.expect(["password for"])
           ssh.sendline(password)
       ssh.expect(pexpect.EOF, timeout=300)
       r = ssh.before
    elif i == 2:
       onlog.error("Shell command nexpected exit (command:" + ssh_cmd + ")")
    elif i == 3:
       onlog.error("Shell command timeout (" + ssh_cmd + ")")
       
    ssh.close()
    onlog.info("Shell Command Done.")
    return r

def ssh_remote_host(host, user, password):
    ssh = 'ssh ' + user + '@' + host

    ssh = pexpect.spawn("/bin/bash", ['-c', ssh])
    i = ssh.expect(['[Pp]assword:', SSH_NEWKEY, pexpect.EOF, pexpect.TIMEOUT])
    if i == 0:
       ssh.sendline(password)
       j = ssh.expect(".*[$#]")
       ssh.send('\n')
       ssh.interact()
    elif i == 1:
       ssh.sendline('yes')
       ssh.expect('[Pp]assword:')
       ssh.sendline(password)
       ssh.expect(".*[$#]")
       ssh.send('\n')
       ssh.interact()
    elif i == 2:
       pass
    elif i == 3:
       pass
       
    ssh.close()
    return

def telnet_remote_host(host):
    telnet_cmd = 'telnet ' + host 
    telnet = pexpect.spawn(telnet_cmd)
    #TODO

def remote_copy(host, user, password, src, dst):
    onlog = logger.getlog()
    retcode = 0
    scp_cmd = 'scp ' + src + ' ' + user + '@' + host + ':' + dst
    onlog.info("Running scp command: " + scp_cmd)
    #print scp_cmd 
    scp = pexpect.spawn("/bin/bash", ['-c', scp_cmd])
    i = scp.expect(['[Pp]assword:', SSH_NEWKEY, pexpect.EOF, pexpect.TIMEOUT], timeout=15)
    #print i
    if i == 0:
       scp.sendline(password)
       scp.expect(pexpect.EOF)
       onlog.info("SCP Done.")
    elif i == 1:
       scp.sendline('yes')
       scp.expect('[Pp]assword:')
       scp.sendline(password)
       scp.expect(pexpect.EOF)
       onlog.info("SCP Done.")
    elif i == 2:
       retcode = -1
       onlog.error("SCP unexpected EOF (command: " + scp_cmd + ")")
    elif i == 3:
       onlog.error("SCP timeout (command: " + scp_cmd + ")")
       retcode = -1
    scp.close()
    return retcode

def get_vmmapping_list():
    for host_info in hosts:
        output = execute_shell_cmd(host_info['host'], 
                                host_info['user'], 
                                host_info['password'], 
                                "cat /.vmmapping")
        global_vm_list[host_info['host']] = []
        for line in output.strip().split(os.linesep):
            mac_vm = line.split('<=>')
            if len(mac_vm) != 2:
                continue
            global_vm_list[host_info['host']].append({'name':mac_vm[1], 
                                                    'mac':mac_vm[0]})

def get_vmname_by_node(node_id):
    # get BMC mac address
    mac_list = get_mac_by_id(node_id)
    return get_vmname_by_mac(mac_list[0])

def get_vmname_by_mac(mac_addr):
    for h in global_vm_list.keys():
        for d in global_vm_list[h]:
            if d['mac'][-5:] == mac_addr[-5:]:
                return h,d['name'].strip('\r')
    return None,None

def create_script():
    current_path = os.getcwd()
    file_path = current_path + "/getvmname.sh"
    if os.path.exists(file_path):
        return
    content = ""
    content += "#!/bin/sh\n"
    content += "if [ ! -e /tmp/.getvmname ];then\n"
    content += "    touch /tmp/.getvmname\n"
    content += "else\n"
    content += "    exit 0\n"
    content += "fi\n"
    content += "\n"
    content += "if [ -e /.vmmapping ];then\n"
    content += "    rm -rf /.vmmapping\n"
    content += "fi\n"
    content += "vim-cmd vmsvc/getallvms > .allvms\n"
    content += "vmids=`cat .allvms | awk '{print $1}' | grep -E \"^[0-9]+\"`\n"
    content += "for id in $vmids\n"
    content += "do\n"
    content += "    macs=`vim-cmd vmsvc/device.getdevices $id | sed -n \'s/^[ \\t]*macAddress = \"\(\([0-9a-z]\{2\}:\)\{5\}[0-9a-z]\{2\}\)\".*/\\1/p\'`\n"
    content += "    vmname=`cat .allvms | grep -E \"$id[ \\t]+\" | awk '{print $2}'`\n"
    content += "    for mac in $macs\n"
    content += "    do\n"
    content += "       echo \"$mac<=>$vmname\">>.vmmapping\n" 
    content += "    done\n"
    content += "done\n"
    content += "rm .allvms\n"
    content += "rm /tmp/.getvmname\n"
    fp = open(file_path, 'w')
    fp.write(content)
    fp.flush()
    fp.close()
    os.chmod(file_path, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)

def delete_script(file_path):
    if os.path.isfile(file_path):
        os.remove(file_path)

def send_and_execute_script(*args):
    host = args[0]
    user = args[1]
    password = args[2]
    if remote_copy(host, user, password, os.getcwd() + "/getvmname.sh", "/") < 0:
        return
    execute_shell_cmd(host, user, password, "/bin/sh /getvmname.sh")

def send_and_execute_scripts():
    create_script()
    threads = []
    for host in hosts:
        t = threading.Thread(target=send_and_execute_script, args=(host['host'], host['user'], host['password']))
        t.setDaemon(True)
        threads.append(t)
   
    for t in threads:
        t.start()

def get_dhcp_info_db(server):
    if server == "localhost":
       dhcp_file = open('/var/lib/dhcp/dhcpd.leases', 'r')
       leases_db = parse_leases_file(dhcp_file)
       dhcp_file.close()
    else:
        output = execute_shell_cmd(server, "onrack", "onrack", "cat /var/lib/dhcp/dhcpd.leases")
        #print output
        leases_db = parse_leases_str(output.strip())
    return leases_db

def show_dhcp_info_all(server):
    leases_db = get_dhcp_info_db(server)
    if len(leases_db) == 0:
       return
    table = Texttable()
    table.header(["No.", "MAC Address", "IP Address"])
    table.set_cols_align(['c', 'c', 'l'])
    table.set_cols_valign(['m', 'm', 'm'])
    table.set_cols_width([4, 17, 15])
    index = 0
    for ip_address in leases_db:
        leases_rec = leases_db[ip_address][0]
        index += 1
        table.add_row([str(index), leases_rec['hardware'], leases_rec['ip_address']])
    table_str = table.draw()
    print table_str
    onlog = logger.getlog()
    onlog.info("\n" + table_str)
    dump_table_to_file("dhcp_leases.txt", table_str)

def show_dhcp_info_active(server):
    leases_db = get_dhcp_info_db(server)
    if len(leases_db) == 0:
       return
    now = timestamp_now()
    report_dataset = select_active_leases(leases_db, now)
    table = Texttable()
    table.header(["No.", "MAC Address", "IP Address", "Expires,H:M:S", "Client\nHostname"])
    table.set_cols_align(['c', 'c', 'l', 'c', 'c'])
    table.set_cols_valign(['b', 'b', 'b', 'b', 'b'])
    index = 0
    for lease in report_dataset:
        index += 1
        table.add_row([str(index), lease['hardware'], lease['ip_address'], \
                str((lease['ends'] - now) if lease['ends'] != 'never' else 'never'), lease['client-hostname']])
    table_str = table.draw()
    print table_str
    onlog = logger.getlog()
    onlog.info("\n" + table_str)
    print GREEN + 'Total Active Leases: ' + str(len(report_dataset)) + NORMAL
    print GREEN + 'Report generated (UTC): ' + str(now) + NORMAL
    dump_table_to_file("dhcp_active_leases.txt", table_str)

def get_ip_address_in_leases(server, mac_addr):
    leases_db = get_dhcp_info_db(server)
    if len(leases_db) == 0:
       return ""
    for ip_address in leases_db:
        leases_rec = leases_db[ip_address][0]
        if leases_rec['hardware'] == mac_addr:
           return leases_rec['ip_address']
    return ""

def dump_table_to_file(filename, table_str):
    table_file_path = os.getcwd() + "/data/" + filename
    if os.path.exists(table_file_path):
        os.rename(table_file_path, table_file_path + ".old")
    table_file = open(table_file_path, "w")
    table_file.write(table_str)
    table_file.flush()
    table_file.close()


def vmpower_control(vmname, action):
    for host_info in hosts:
        cmd = 'vim-cmd vmsvc/getallvms | grep -w ' + vmname + ' | ' + 'awk \'{print $1}\''
        vmid = execute_shell_cmd(host_info['host'], host_info['user'], host_info['password'], cmd)
        #print vmid.strip()
        if vmid.strip() != "":
           action_cmd = 'vim-cmd vmsvc/power.' + action + ' ' + vmid.strip()
           output = execute_shell_cmd(host_info['host'], host_info['user'], host_info['password'], action_cmd)
           print output

def forward_preinit():
    pre_routing = "sudo iptables -t nat -F PREROUTING"
    post_routing = "sudo iptables -t nat -F POSTROUTING"
    input_enable = "sudo iptables -P INPUT ACCEPT"
    forward_enable = "sudo iptables -P FORWARD ACCEPT"
    ip_forward = "sudo sysctl net.ipv4.ip_forward=1"
    rules = [pre_routing, post_routing, input_enable, forward_enable, ip_forward]
    time1 = 0.0
    time2 = 0.0
    time1 = time.time()
    for rule in rules:
        execute_shell_cmd(rackhd_server, "onrack", "onrack", rule, True)
    time2 = time.time()
    print "Preinit command consume %f" % (round(time2 - time1, 2))

# Add portforwarding functionality
def forward_vnc_port(bmc_ip):
    if bmc_ip == "":
        return ""

    #cmd = "which iptables"
    #iptables = execute_shell_cmd(rackhd_server, "onrack", "onrack", cmd)
    #if iptables == '':
    #    print RED + "no iptables command... system exit..."
    #    print RED + "please install iptables command before running the application"
    #    print RED + "try  sudo apt-get install iptables"
    #    sys.exit(0)

    dst_port = 5901
    sub_fields = bmc_ip.split('.')
    src_port = '{0}{1:03}'.format(int(sub_fields[2]) % 100, int(sub_fields[3]))
    prerouting = "sudo iptables -A PREROUTING -t nat -p tcp --dport " + src_port + \
    		 " -j DNAT --to " + bmc_ip + ":" + str(dst_port)
    postrouting = "sudo iptables -t nat -A POSTROUTING -d " + bmc_ip + " -p tcp --dport " + \
                    str(dst_port) + " -j MASQUERADE"
    time1 = 0.0
    time2 = 0.0
    time1 = time.time()
    execute_shell_cmd(rackhd_server, "onrack", "onrack", prerouting, True)
    execute_shell_cmd(rackhd_server, "onrack", "onrack", postrouting, True)
    time2 = time.time()
    print "Port forwarding for %s consumes %f" % (bmc_ip, round(time2 - time1, 2))
    return src_port

class MonorailTestCommand(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = YELLOW + "> " + NORMAL
        self.onlog = logger.getlog()
        self.intro = RED + "Please update the config file [conf/host.conf] per your environment prior to runing this script!\nYou can also use 'conf' to update the config, run 'help conf' for more help."

    def emptyline(self):
        return #cmd.Cmd.emptyline(self)

    def do_list(self, arg):
        time1 = time.time()
        get_vmmapping_list()
        if monorail_node_list() < 0:
            return 

        time2 = time.time()
        if get_node_ip_list() < 0:
            return
        time3 = time.time()
        delta1 = round(time2 - time1, 3)
        delta2 = round(time3 - time2, 3)
        discovered_nodes = len(global_node_list)
        if arg == "":
            show_node_list()
            print
            print GREEN + 'Report generated (UTC): ' + time.ctime() + NORMAL
            print GREEN + "It takes " + str(delta1+delta2) + "[" + str(delta1) + "/" + str(delta2) +"] seconds to discover " \
                    + str(discovered_nodes) + " nodes" + NORMAL
        elif arg == "failed":
            args_list = arg.strip().split(' ')
            if args_list[0] == "failed":
                nodes_without_bmc = show_node_list_without_bmc()
                print
                print GREEN + 'Report generated (UTC): ' + time.ctime() + NORMAL
                print GREEN + "It takes " + str(delta1+delta2) + "[" + str(delta1) + "/" + str(delta2) +"] seconds to discover " \
                        + str(discovered_nodes) + " nodes, " + str(nodes_without_bmc) + " nodes have node BMC info." + NORMAL
        elif arg == "unknown":
            pass

    def help_list(self):
        print "list         - List all nodes"
        print "list failed  - List the nodes without bmc info"

    def do_delete(self, arg):
        if arg == "":
            delete_node_list()
        else:
            # get the id
            args_list = arg.strip().split(' ')
            if len(args_list) == 1:
                node_id = get_node_id_re(args_list[0])
                if node_id == "":
                    return

                mac_list = get_mac_by_id(node_id)
                if len(mac_list) == 0:
                    return

                for mac in mac_list:
                    delete_node_lookups(mac)

                delete_node(node_id)
            else:
                print "Unsupport parameter: " + arg

    def help_delete(self):
        print "delete           - delete all nodes"
        print "delete <node id> - delete node"

    def do_catalogs(self, arg):
        if arg == "":
            monorail_node_catalogs()
        else:
            args_list = arg.lower().strip().split(' ')
            node_id = get_node_id_re(args_list[0])
            if node_id == "":
                return

            args_len = len(args_list)
            if args_len == 1:
                monorail_node_catalogs_id(node_id, True)
            elif args_len == 2:
                monorail_node_catalogs_source(node_id, args_list[1])
            else:
                print "Unsupport parameter: " + arg

    def help_catalogs(self):
        print "catalogs             - get all nodes catalogs"
        print "catalogs <node id>   - get one node catalogs"

    def do_workflow(self, arg):
        if arg == "":
            return
        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        subcmd = args_list[0]
        if subcmd == "list":
            monorail_workflows_library_get()
        else:
            if args_len < 2:
                return
            node_id = get_node_id_re(args_list[1])
            if node_id == "":
                return

            if subcmd == "get":
                monorail_node_workflows_get(node_id)
            elif subcmd == "set":
                monorail_node_workflow_set(node_id, args_list[2])
            elif subcmd == "delete":
                monorail_node_workflows_active_delete(node_id)
            elif subcmd == "active":
                monorail_node_workflows_active_get(node_id)
            else:
                print "Unsupport parameter: " + arg

    def help_workflow(self):
        print "workflow get <node id>          - get node workflow"
        print "workflow set <node id> <action> - set node workflow"
        print "workflow delete <node id>       - delete active workflow"
        print "workflow active <node id>       - get active workflow"
        print "workflow list                   - get all available workflows"

    def do_lookups(self, arg):
        if arg == "":
            get_node_ip_list()
            show_node_ip_list()
        else:
            args_list = arg.strip().split(' ')
            args_len = len(args_list)
            mac_address=""
            ipaddr = ""
            dhcp_id = ""
            if args_list[0] == "id" and args_len == 2:
                node_id = get_node_id_re(args_list[1])
                if node_id == "":
                    return
                mac_address, ipaddr, dhcp_id = monorail_lookups_ip_get(node_id)
            elif args_list[0] == "mac" and args_len == 2:
                mac_address, ipaddr, dhcp_id = monorail_lookups_ip_get(args_list[1])
            else:
                print "Unsupport parameters: " + arg
                return

            if dhcp_id == "":
                print "No DHCP info found."
                return

            table = Texttable()
            table.add_row([dhcp_id, mac_address, ipaddr])
            print table.draw()

    def help_lookups(self):
        print "lookups                      - show all node ip(nested QEMU)"
        print "lookups id <node id>         - display ip per node id"
        print "lookups mac <mac adr>        - display ip per mac address"

    def do_getobm(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len != 1:
            return

        node_id = get_node_id_re(args_list[0])
        if node_id == "":
            return

        monorail_node_obm_get(node_id)

    def help_getobm(self):
        print "getobm <node id>  - get obm settings for node"

    def do_setobm(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        args_len = len(args_list)

        if args_len > 3:
            return
        else:
            node_id = get_node_id_re(args_list[0])
            if node_id == "":
                return

            bmc_ip = args_list[1]
            if args_len == 2:
                monorail_node_obm_set(node_id, bmc_ip)
            elif args_len == 4:
                user = args_list[2]
                password = args_list[3]
                monorail_node_obm_set(node_id, bmc_ip, user, password)
            else:
                return

    def help_setobm(self):
        print "setobm <node id> <bmc ip> [user] [password]  - set obm settings for node"

    def do_bmcip(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len > 1:
            return
        else:
            node_id = get_node_id_re(args_list[0])
            if node_id == "":
                return

            print GREEN + get_bmc_ip(node_id) + NORMAL

    def help_bmcip(self):
        print "bmcip <node id>  - get bmc ip for node"

    def do_pollers(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len > 1:
            return
        else:
            node_id = get_node_id_re(args_list[0])
            if node_id == "":
                return

            monorail_pollers_command_list(node_id)

    def help_pollers(self):
        print "pollers <node id>    - get pollers for node"

    def do_tasks(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        if args_list[0] == "list":
            monorail_workflowtasks_library()
        else:
            print "Currently not support args: " + arg

    def help_tasks(self):
        print "tasks list   - get all tasks"

    def do_getvm(self, arg):
        if arg == "":
            return

        args_list = arg.split(' ')
        args_len = len(args_list)

        if args_len > 3:
            return
        else:
            vmname = ""
            ip_address = ""
            host_address = ""
            pair = None
            subcmd = args_list[0]
            get_vmmapping_list()
            if subcmd == "id":
                node_id = get_node_id_re(args_list[1])
                if node_id == "":
                    return
                vmname, host_address  = get_vmname_by_node(node_id)
                if vmname == None:
                    print RED + "Please wait a while and try it again!" + NORMAL
                    return

                #ip_address = get_ip_address_in_leases(rackhd_server, mac_addr)
            elif subcmd == "mac":
                host_address, vmname = get_vmname_by_mac(args_list[1])
                if vmname == None:
                    print RED + "Please wait a while and try it again!" + NORMAL
                    return
                #ip_address = get_ip_address_in_leases(rackhd_server, args_list[1])
            print GREEN + "+------------------------------------------------+" + NORMAL
            print GREEN + "| " + format(vmname, '<16') + " | " + format(host_address, "<15") + " | " + NORMAL
            print GREEN + "+------------------------------------------------+" + NORMAL

    def help_getvm(self):
        print "getvm id <node id>       - get VM name by node id"
        print "getvm mac <mac addr>     - get VM name by mac address"

    def do_vmpower(self, arg):
        if arg == "":
            return

        args_list = arg.split(' ')
        args_len = len(args_list)

        if args_len > 2:
            return
        action = args_list[0]
        vmname = args_list[1]
        if action == "on" or action == "off" or action == "reset" \
            or action == "reboot" or action == "getstate":
                vmpower_control(vmname, action)
        else:
            return

    def help_vmpower(self):
        print "vmpower <action> <vm name>       - control VM"
        print " action - on/off/reset/reboot/getstate"

    def do_lsdhcp(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len > 1:
            return
        subcmd = args_list[0]
        if subcmd == "all":
            show_dhcp_info_all(rackhd_server)
        elif subcmd == "active":
            show_dhcp_info_active(rackhd_server)

    def help_lsdhcp(self):
        print "lsdhcp all       - display all leases"
        print "lsdhcp active    - display active leases" 

    def do_conf(self, arg):
        if arg == "":
            return
        args_list = arg.strip().split(' ')
        subcmd = args_list[0]
        config_path = os.getcwd() + "/conf/hosts.conf"
        args_len = len(args_list)

        if subcmd == "list":
            read_config(config_path, True)
        elif subcmd == "load":
            load_config(config_path)
        elif subcmd == "update" and args_len == 4:
            section = args_list[1]
            option = args_list[2]
            value = args_list[3]
            update_option(config_path, section, option, value)
        elif subcmd == "add" and args_len == 5:
            section = args_list[1]
            host = args_list[2]
            user = args_list[3]
            password = args_list[4]
            add_section(config_path, section, host, user, password)
        elif subcmd == "del" and args_len == 2:
            section = args_list[1]
            delete_section(config_path, section)

    def help_conf(self):
        print "conf list                                    - List current configuration"
        print "conf load                                    - Load the configuration"
        print "conf del <section>                           - Delete one section"
        print "                                               e.g."
        print "                                               conf del RackHD Server"
        print "conf update <section> <option> <value>       - Update the configuration"
        print "                                               e.g."
        print "                                               conf update RackHD Server host xxx.xxx.xxx.xxx"
        print "conf add <section> <host> <user> <password>  - Add one section"
        print "                                               e.g."
        print "                                               conf add esxihost0 xxx.xxx.xxx.xxx root 1234567"

    def do_ssh(self, arg):
        if arg == "":
            return
        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len != 3:
            return
        ssh_remote_host(args_list[0], args_list[1], args_list[2])

    def help_ssh(self):
        print "ssh <host> <user> <password>"

    def do_onconfig(self, arg):
        if arg == "":
            return

        args_list = arg.strip().split(' ')
        if args_list[0] != "get":
            return

        monorail_config_get()

    def help_onconfig(self):
        print "onconfig get"

    def do_versions(self, arg):
        if arg != "":
            return
        monorail_versions_get()

    def help_versions(self):
        print "versions     - get all rackhd component versions"

    def do_skus(self, arg):
        if arg == "":
            return
        args_list = arg.strip().split(' ')
        args_len = len(args_list)
        if args_len > 1:
            return
        else:
            if args_list[0] == "list":
                monorail_skus_list()
            else:
                monorail_skus_nodes_list(args_list[0])

    def help_skus(self):
        print "skus <list>/<sku id>"

    def do_quit(self, arg):
        delete_script(os.getcwd() + "/getvmname.sh")
        return True

    def help_quit(self):
        print "Exit the script"

    def do_shell(self, arg):
        sub_cmd = subprocess.Popen(arg, shell=True, stdout = subprocess.PIPE)
        print sub_cmd.communicate()[0]
    
    def do_vmlist(self, arg):
        get_vmmapping_list()

        forward_preinit()
        table = Texttable()
        table.set_cols_align(['c', 'c', 'l', 'l', 'c'])
        table.set_cols_valign(['m', 'm', 'm', 'm', 'm'])
        table.set_cols_width([17, 32, 17, 15, 6])  
        table.header(["ESXI host", "VM Name", "vBMC MAC", "IP", "VNC Port"])

        for h in global_vm_list.keys():
            #print "VMs on %s" % h
            for d in global_vm_list[h]:
                if "onrack" in d['name'].lower():
                    table.add_row([h, d['name'], d['mac'], "None", "None"])
                else:
                    mac_address, ipaddr, dhcp_id = monorail_lookups_ip_get(d['mac'])
                    src_port = forward_vnc_port(ipaddr)
                    table.add_row([h, d['name'], d['mac'], ipaddr, src_port])
        print table.draw()

    def do_uvm(self, arg):
        get_vmmapping_list()
        if monorail_node_list() < 0:
            print "Get node list failed."
            return

        unknown_list = []
        for h in global_vm_list.keys():
            for d in global_vm_list[h]:
                found = False
                #print 'Checking %s' % d['name']
                for node in global_node_list:
                    for mac in node['identifier']:
                        if d['mac'][-5:] == mac[-5:]:
                            found = True
                            break
                    if found:
                        break
                if not found:
                    #print h, d['name']
                    unknown_list.append({'name':d['name'], 'esxi':h})
        
        if len(unknown_list) == 0:
            print "No unknown nodes, wait a while and try it again."
            return

        table = Texttable()
        table.header(['ESXi host', 'VM Name'])

        new_unknown_list = [dict(t) for t in set([tuple(d.items()) for d in unknown_list])]
        for uv in new_unknown_list:
            table.add_row([uv['esxi'], uv['name']])
        print table.draw()

    def help_uvm(self):
        print "uvm - list all unknown nodes."

    def help_vmlist(self):
        print "vmlist - list all virtual machines."

    def do_ipmitool(self, arg):
        if arg == "":
            return 

        command = "ipmitool {0}".format(arg)
        execute_shell_cmd(rackhd_server, "onrack", "onrack", command)

    def help_ipmitool(self):
        print "ipmitool - see ipmitool help document"

    def precmd(self, arg):
        self.onlog.info("Test command: " + arg)
        return cmd.Cmd.precmd(self, arg)

    def default(self, arg):
        self.onlog.error("Unknown command: " + arg)
        return

if __name__ == '__main__':
    logger = Logger("./monorailtest.log", loglevel=1, logger="MonorailTest")
    onlog = logger.getlog()
    onlog.info("Starting ...")
    config_path = os.getcwd() + "/conf/hosts.conf"
    if not read_config(config_path, False):
        sys.exit(1)
    send_and_execute_scripts()
    MTC = MonorailTestCommand()
    MTC.cmdloop()
