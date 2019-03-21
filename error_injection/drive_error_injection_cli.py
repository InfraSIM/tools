#!/usr/bin/env python

import cmd
import sys
import socket
import argparse
import os
import json
import re
from copy import deepcopy


line = """
==========================================================================
"""

errorinjection_help = """
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Support commands:
    list          List all device id
    nvme          Inject error
    show          Show error status for all device
    nvmeclear     Clean error
    scsi_logpage  Inject data to logpage
    scsi_status   Inject scsi status error
    scsiclear     Clear scsi error
    history       Show qmp command history
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""

nvmeclear_help = """
usage: nvmeclear <id>

clear nvme error on a device

"""

history_command=[]


def connect_monitor(monitor_file):
    if not os.path.exists(monitor_file):
        return None
    monitor = Monitor(monitor_file)
    try:
        monitor.connect()
    except IOError:
        return None
    return monitor

def get_device_list(monitor, device_type):
    payload = {
        "execute": "human-monitor-command",
        "arguments":{
            "command-line":"info block"
        }
    }
    monitor.send(payload)
    results = monitor.recv()
    if 'error' not in str(results):
        returns = results.get('return')
        device_list = re.findall(r'Attached to:\s+(\S+)', returns, re.M)
        return [x for x in device_list if device_type in x]
    else:
        return None

def get_device_list_info(monitor, device_list):
    payload = {
            "execute": "human-monitor-command",
            "arguments": {
                "command-line": "info qtree"
                }
            }
    monitor.send(payload)
    results = monitor.recv()
    dev_list_info = {}
    returns = str(results.get('return')).split("dev:")[1:]
    for device_id in device_list:
        for dev in returns:
            if device_id in dev:
                dev_list_info[device_id] = re.findall(r'serial = "(\S+)"', dev)[0]
                break
    return dev_list_info

class Monitor(object):

    def __init__(self, path):
        self.path = path
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.s.connect(self.path)
        self.recv()
        payload = {
            "execute": "qmp_capabilities"
        }
        self.send(payload)
        self.recv()

    def send(self, payload):
        self.s.send(json.dumps(payload))

    def recv(self):
        while 1:
            rsp = ""
            while 1:
                snip = self.s.recv(1024)
                rsp += snip
                if len(snip) < 1024:
                    break
            if "timestamp" not in rsp:
                break

        return json.loads(rsp)

    def close(self):
        self.s.shutdown(2)
        self.s.close()

    def shutdown_recv(self):
        self.s.shutdown(0)



def list_argparse():
    parser = argparse.ArgumentParser(prog="list",
                                     usage="list all device id")
    parser.add_argument("-u", "--update", action="store", required=False,
                        help="update nvme device id")
    return parser

def nvmeclear_argparse():
    parser = argparse.ArgumentParser(prog="nvmeclear")
    parser.add_argument("-i", "--id", action="store", required=False,
                        default=None, help="nvme device id")
    return parser

def scsiclear_argparse():
    parser = argparse.ArgumentParser(prog="scsiclear")
    parser.add_argument("-i", "--id", action="store", required=False,
                        default=None, help="scsi device id")
    return parser

def nvme_argparse():
    parser = argparse.ArgumentParser(prog="nvme")
    parser.add_argument("-i", "--id", action="store", required=False,
                        default=None, help="nvme device id")
    parser.add_argument("-n", "--nsid", action="store", required=False,
                        default=1, help="nvme namespace id")
    parser.add_argument("-s", "--sc", action="store", required=False,
                        default=None, help="status code")
    parser.add_argument("-t", "--sct", action="store", required=False,
                        default=None, help="status code type")
    error_help = "Support nvme error type: {}".format(", ".join(error_map.keys()))
    parser.add_argument("-e", "--error", action="store", required=False,
                        default=None, help=error_help)
    parser.add_argument("-m", "--more", action="store", required=False,
                        default=True, help="more info in Error Information log")
    parser.add_argument("-d", "--dnr", action="store", required=False,
                        default=True, help="do not retry")
    opcode_help = "support : flush, write, read, write_uncor, \
                                compare, write_zeros, dsm, rw"
    parser.add_argument("-o", "--opcode", action="store", required=False,
                        default="rw", help=opcode_help)
    parser.add_argument("-c", "--count", action="store", required=False,
                        default=65536, help="error inject available times")
    parser.add_argument("-l", "--lbas", action="store", required=False,
                        help="logical block address")
    return parser

def scsi_logpage_argparse():
    parser = argparse.ArgumentParser(prog="scsi_logpage")
    parser.add_argument("-i", "--id", action="store", required=False,
                        default=None, help="scsi device id")
    error_help = "support page type: life_used, erase_count, temperature"
    parser.add_argument("-t", "--type", action="store", required=True,
                        default=None, help=error_help)
    parser.add_argument("-a", "--action", action="store", required=True,
                        default=None, help="support actions: add, remove, modify")
    parser.add_argument("-p", "--parameter", action="store", required=False,
                        default=None, help="parameter in logpage")
    parser.add_argument("-pl", "--parameter_len", action="store", required=False,
                        default=4, help="parameter length in byte")
    parser.add_argument("-v", "--value", action="store", required=False,
                        default=None, help="scsi device id")
    return parser

def scsi_status_argparse():
    parser = argparse.ArgumentParser(prog="scsi_status", formatter_class=argparse.RawTextHelpFormatter,
                                     description='Inject status error to drive. Injected error will cleaned automatically after cli exit.')
    parser.add_argument("-i", "--id", action="store", required=False,
                        default=None, help="scsi device id")
    error_types = ["check-condition", "condition-met", "busy", "reservation-conflict",
                   "task-set-full", "aca-active", "task-aborted"]
    parser.add_argument("-c", "--count", action="store", required=False,
                        default=65536, help="error inject available times")
    parser.add_argument("-t", dest="type", action="store", required=False,
                        choices=error_types,
                        default="busy",
                        metavar='TYPE',
                        help="scsi status error type:\n" + "\n".join(error_types))

    parser.add_argument("-l", "--lbas", action="store", required=False,
                        default=0, help="lbas list")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--sense", action="store", required=False, metavar='N',
                        default=None, type=lambda x: int(x, 0), nargs=3, help="sense_code [key asc ascq].\nRefer to https://en.wikipedia.org/wiki/Key_Code_Qualifier")
    error_keys = scsi_status_error_map.keys()
    error_help = "Supported scsi sense code string:\n{}".format("\n".join(error_keys))
    group.add_argument("-e", "--error", action="store", required=False, metavar='ERROR',
                       choices=error_keys, default=None, help=error_help)
    return parser

def history_record(command):
    history_command.append(command)

def show_record():
    for cmd in history_command:
        print cmd

class ErrorInjectCli(cmd.Cmd):
    def __init__(self, monitor):
        cmd.Cmd.__init__(self)
        self._monitor = monitor
        self._list_args = None
        self._nvme_args = None
        self._scsi_args = None
        self._nvmeclear_args = None
        self.prompt = "EI> "
        self._nvme_id_list_injected = {}
        self._scsi_id_list_injected = {}
        self._nvme_id_list_all = []

    def init(self):
        self._nvme_id_list_all = get_device_list(self._monitor, "nvme")
        self._scsi_id_list_all = get_device_list(self._monitor, 'scsi')
        self._list_args = list_argparse()
        self._nvme_args = nvme_argparse()
        self._scsi_logpage_args = scsi_logpage_argparse()
        self._scsi_status_args = scsi_status_argparse()
        self._nvmeclear_args = nvmeclear_argparse()
        self._scsiclear_args = scsiclear_argparse()

    def do_show(self, args):
        for id in self._nvme_id_list_all:
            if self._nvme_id_list_injected.has_key(id):
                error = self._nvme_id_list_injected[id]
                out_str = "{} {}".format(id, error)
            else:
                out_str = "{} NoError".format(id)
            print out_str
        for id in self._scsi_id_list_all:
            if self._scsi_id_list_injected.has_key(id):
                error = self._scsi_id_list_injected[id]
                out_str = "{} {}".format(id, error)
            else:
                out_str = "{} NoError".format(id)
            print out_str

    def do_history(self, args):
        show_record()
    def emptyline(self):
        return ""
    def do_help(self, args):
        if args:
            if args == "nvme":
                self.do_nvme("--help")
            if args == "scsi_logpage":
                self.do_scsi_logpage("--help")
            elif args == "nvmeclear":
                self.do_nvmeclear("--help")
            elif args == "list":
                self.do_list("--help")
            else:
                return
        else:
            print errorinjection_help
            self.do_nvme("--help")
            print line
            self.do_nvmeclear("--help")
            print line
            self.do_list("--help")
            print line
            self.do_scsi_logpage("--help")
            print line
            self.do_scsi_status('--help')

    def do_nvmeclear(self, args):
        args_list = args.split()
        try:
            parseargs = self._nvmeclear_args.parse_args(args_list)
        except SystemExit as e:
            return

        if parseargs.id:
            nvme_args = "-i {} -n 0 -s 0 -t 0 -c 0".format(parseargs.id)
            self.do_nvme(nvme_args)
        else:
            # clear all device error
            nvme_dict = self._nvme_id_list_injected
            for key in nvme_dict.keys():
                nvme_args = "-i {} -n 0 -s 0 -t 0 -c 0".format(key)
                self.do_nvme(nvme_args)

    def do_scsiclear(self, args):
        args_list = args.split()
        try:
            parseargs = self._scsiclear_args.parse_args(args_list)
        except SystemExit as e:
            return

        if parseargs.id:
            scsi_args = "-i {} -c 0".format(parseargs.id)
            self.do_scsi_status(scsi_args)
        else:
            # clear all device error
            scsi_dict = self._scsi_id_list_injected
            for key in scsi_dict.keys():
                scsi_args = "-i {} -c 0".format(key)
                self.do_scsi_status(scsi_args)


    def do_nvme(self, args):
        args_list = args.split()
        try:
            parseargs = self._nvme_args.parse_args(args_list)
        except SystemExit as e:
            return

        monitor = self._monitor
        if parseargs.error and error_map.has_key(parseargs.error):
            parseargs.sc = error_map[parseargs.error]['sc']
            parseargs.sct = error_map[parseargs.error]['sct']
            if  error_map[parseargs.error].has_key('opcode'):
                parseargs.opcode = error_map[parseargs.error]['opcode']
        elif parseargs.sc is None or parseargs.sct is None:
            print "[Error]: please at least config (SC & SCT) or (ERROR)"
            print "eg: nvme -e internal-error"
            print line
            self.do_nvme("--help")
            return

        # check sc and sct validition
        status_field = {
            "sc": int(parseargs.sc),
            "sct": int(parseargs.sct),
            "more": parseargs.more,
            "dnr": parseargs.dnr
        }
        cmd = {
            "nsid": int(parseargs.nsid),
            "status_field": status_field,
            "opcode": parseargs.opcode,
            "count": int(parseargs.count),
        }
        if parseargs.lbas:
            cmd['lbas'] = [int(parseargs.lbas)]

        cmd_list = []
        if not parseargs.id: # not set id, will inject to all drive
            for id in self._nvme_id_list_all:
                cmd_new = deepcopy(cmd)
                cmd_new['id'] = id
                cmd_list.append(cmd_new)
        else:
            cmd['id'] = parseargs.id
            cmd_list.append(cmd) # only one cmd

        for command in cmd_list:
            payload = {
                "execute": "nvme-status-code-error-inject",
                "arguments": command
            }
            monitor.send(payload)
            results = monitor.recv()
            if 'error' not in str(results):
                if command["count"]:
                    print "Inject Done: {}".format(command['id'])
                    self._nvme_id_list_injected[command['id']] = parseargs.error
                else:
                    print "Clean Done: {}".format(command["id"])
                    self._nvme_id_list_injected.pop(command['id'])
                record = 'Inject Success: {}'.format(command)
            else:
                print results
                record = 'Inject Failed: {}'.format(command)
            history_record(record)

    def do_list(self, args):
        args_list = args.split()
        try:
            parseargs = self._list_args.parse_args(args_list)
        except SystemExit as e:
            return
        if parseargs.update:
            print '<<<<<<<<<<<<<< update device id >>>>>>>>>>>>>>>'
            self._nvme_id_list_all = get_device_list(self._monitor, 'nvme')
            self._scsi_id_list_all = get_device_list(self._monitor, 'scsi')

        nvme_device_info = get_device_list_info(self._monitor, self._nvme_id_list_all)
        scsi_device_info = get_device_list_info(self._monitor, self._scsi_id_list_all)

        for id in self._nvme_id_list_all:
            print id, "({})".format(nvme_device_info.get(id, None))
        for id in self._scsi_id_list_all:
            print id, "({})".format(scsi_device_info.get(id, None))

    def do_scsi_logpage(self, args):
        args_list = args.split()
        try:
            parseargs = self._scsi_logpage_args.parse_args(args_list)
        except SystemExit as e:
            return

        monitor = self._monitor
        if 'add' in parseargs.type and not parseargs.value:
            print 'Error: add need a value'
            return
        # check sc and sct validition
        cmd = {
            "type": parseargs.type,
            "action": parseargs.action,
        }
        if parseargs.parameter:
            cmd['parameter'] = int(parseargs.parameter)

        if parseargs.parameter_len:
            cmd['parameter_length'] = int(parseargs.parameter_len)

        if parseargs.value:
            cmd['val'] = int(parseargs.value)

        cmd_list = []
        if not parseargs.id: # not set id, will inject to all drive
            for id in self._scsi_id_list_all:
                cmd_new = deepcopy(cmd)
                cmd_new['id'] = id
                cmd_list.append(cmd_new)
        else:
            cmd['id'] = parseargs.id
            cmd_list.append(cmd) # only one cmd

        for command in cmd_list:
            payload = {
                "execute": "scsi-drive-error-inject",
                "arguments": command
            }
            monitor.send(payload)
            results = monitor.recv()
            if 'error' not in str(results):
                record = 'Inject Success: {}'.format(command)
            else:
                print results
                record = 'Inject Failed: {}'.format(command)
            history_record(record)

    def do_scsi_status(self, args):
        args_list = args.split()
        try:
            parseargs = self._scsi_status_args.parse_args(args_list)
        except SystemExit as e:
            return

        monitor = self._monitor
        cmd = {}
        if parseargs.error or parseargs.sense:
            print "[Warning]: type is set to 'check-condition' when error or sense is specified."
            parseargs.type = "check-condition"
            if parseargs.error:
                sense_key = scsi_status_error_map[parseargs.error]['key']
                sense_asc = scsi_status_error_map[parseargs.error]['asc']
                sense_ascq = scsi_status_error_map[parseargs.error]['ascq']
            if parseargs.sense:
                sense_key = parseargs.sense[0]
                sense_asc = parseargs.sense[1]
                sense_ascq = parseargs.sense[2]

            # check sc and sct validition
            sense_field = {
                "key": sense_key,
                "asc": sense_asc,
                "ascq": sense_ascq,
            }
            cmd['sense'] = sense_field

        cmd["count"] = int(parseargs.count)
        cmd["error_type"] = parseargs.type
        if parseargs.lbas:
            cmd['lbas'] = [int(parseargs.lbas)]

        cmd_list = []
        if not parseargs.id: # not set id, will inject to all drive
            for id in self._scsi_id_list_all:
                cmd_new = deepcopy(cmd)
                cmd_new['id'] = id
                cmd_list.append(cmd_new)
        else:
            cmd['id'] = parseargs.id
            cmd_list.append(cmd) # only one cmd
        for cmd in cmd_list:
            print(cmd)

        for command in cmd_list:
            payload = {
                "execute": "scsi-status-code-error-inject",
                "arguments": command
            }
            monitor.send(payload)
            results = monitor.recv()
            if 'error' not in str(results):
                record = 'Inject Success: {}'.format(command)
                if command["count"]:
                    print "Inject Done: {}".format(command['id'])
                    self._scsi_id_list_injected[command['id']] = parseargs.type
                else:
                    print "Clean Done: {}".format(command["id"])
                    if command['id'] in self._scsi_id_list_injected:
                        self._scsi_id_list_injected.pop(command['id'])
            else:
                print results
                record = 'Inject Failed: {}'.format(command)
            history_record(record)

    def do_quit(self, args):
        self.do_nvmeclear("")
        self.do_scsiclear("")
        return True

    def do_exit(self, args):
        self.do_nvmeclear("")
        self.do_scsiclear("")
        sys.exit(0)


scsi_status_error_map = {
    # add more error type here if needed
    'medium-error': {'key':3, 'asc':17, 'ascq':0}
}


error_map = {
    'data_transfer_error': {'sc':4, 'sct':0},
    'commands-aborted': {'sc':5, 'sct':0},
    'internal-error': {'sc':6, 'sct':0},
    'namespace-not-ready': {'sc':130, 'sct':0},
    'format-in-process': {'sc':131, 'sct':0},
    'write-fault': {'sc':128, 'sct':2, 'opcode':'write'},
    'unrecovered-read-error': {'sc':129, 'sct':2, 'opcode':'read'},
    'endtoend-guard-check-error': {'sc':130, 'sct':2, 'opcode':'read'},
    'endtoend-application-tag-check-error': {'sc':131, 'sct':2},
    'endtoend-reference-tag-check-error': {'sc':132, 'sct':2},
    'compare-failure': {'sc':133, 'sct':2},
    'access-denied': {'sc':134, 'sct':2},
    'deallocated-or-unwritten': {'sc':135, 'sct':2}
}


def main():
    description = "Attention: '-N' or '-M' could not appear together!"
    parser = argparse.ArgumentParser(description = description)
    parser.add_argument("-N", "--nodename", action="store", required=False,
                             help="node name")
    parser.add_argument("-M", "--monitor", action="store", required=False,
                             help="path of .monitor")
    args = parser.parse_args()

    if not (not args.nodename) ^ (not args.monitor):
        print "[ERROR] -N or -M need to be set, (can only choose one!)"
        return

    if args.nodename:
        monitor_path = os.path.join(os.environ['HOME'],
                                    ".infrasim", args.nodename,
                                    '.monitor')
    else:
        monitor_path = args.monitor

    if not os.path.exists(monitor_path):
        print "Could not find monitor file {}".format(monitor_path)
        return

    monitor = connect_monitor(monitor_path)
    if not monitor:
        print "Could not connect to monitor!"
        return

    cli = ErrorInjectCli(monitor)
    cli.init()
    try:
        cli.cmdloop()
    except KeyboardInterrupt as e:
        print "receive keyboard interrupt, will exit"
        cli.do_exit(None)


if __name__ == '__main__':
    main()
