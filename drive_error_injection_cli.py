#!/usr/bin/env python

import cmd
import sys
import socket
import argparse
import os
import json
import re


errorinjection_help = """
==========================================================================
Support commands:
    nvmeclear     Clean error
    nvme          Inject error
==========================================================================
"""

nvmeclear_help = """
usage: nvmeclear

clear nvme error

"""


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


class ErrorInjectCli(cmd.Cmd):
    def __init__(self, monitor):
        cmd.Cmd.__init__(self)
        self._monitor = monitor
        self._nvmeargs = None
        self.prompt = "EI> "
        self._last_nvme_cmd = None

    def nvme_argparse(self):
        parser = argparse.ArgumentParser(prog="nvme")
        parser.add_argument("-i", "--id", action="store", required=True,
                            help="nvme device id")
        parser.add_argument("-n", "--nsid", action="store", required=True,
                            help="nvme namespace id")
        parser.add_argument("-s", "--sc", action="store", required=True,
                            help="status code")
        parser.add_argument("-t", "--sct", action="store", required=True,
                            help="status code type")
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
        self._nvmeargs = parser

    def do_help(self, args):
        if args:
            if args == "nvme":
                self.do_nvme("--help")
            elif args == "nvmeclear":
                print nvmeclear_help
            else:
                return
        else:
            print errorinjection_help
            print nvmeclear_help
            self.do_nvme("--help")

    def do_nvmeclear(self, args):
        if self._last_nvme_cmd:
            nvmeargs = re.sub(r'-c\s+\w+', '-c 0', self._last_nvme_cmd)
            if nvmeargs == self._last_nvme_cmd:
                nvmeargs += ' -c 0'
            self.do_nvme(nvmeargs)
        else:
            return

    def do_nvme(self, args):
        args_list = args.split()
        try:
            parseargs = self._nvmeargs.parse_args(args_list)
        except SystemExit as e:
            return

        monitor = self._monitor
        status_field = {
            "sc": int(parseargs.sc),
            "sct": int(parseargs.sct),
            "more": parseargs.more,
            "dnr": parseargs.dnr
        }
        cmd = {
            "id": parseargs.id,
            "nsid": int(parseargs.nsid),
            "status_field": status_field,
            "opcode": parseargs.opcode,
            "count": int(parseargs.count),
        }
        if parseargs.lbas:
            cmd['lbas'] = [int(parseargs.lbas)]

        #print json.dumps(cmd)
        payload = {
            "execute": "nvme-status-code-error-inject",
            "arguments": cmd
        }
        monitor.send(payload)
        results = monitor.recv()
        if 'error' not in str(results):
            if cmd["count"]:
                print "Inject Done"
                self._last_nvme_cmd = args
            else:
                print "Clean Done"
        else:
            print results

    def do_scsi(self, args):
        pass

    def do_quit(self, args):
        return True

    def do_exit(self, args):
        sys.exit(0)


def connect_monitor(monitor_file):
    if not os.path.exists(monitor_file):
        return None
    monitor = Monitor(monitor_file)
    try:
        monitor.connect()
    except IOError:
        return None
    return monitor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-M", "--monitor", action="store", required=True,
                             help="Server BMC IP address")
    args = parser.parse_args()

    monitor = connect_monitor(args.monitor)
    if not monitor:
        print "Could not connect to monitor!"
        return

    cli = ErrorInjectCli(monitor)
    cli.nvme_argparse()
    cli.cmdloop()


if __name__ == '__main__':
    main()
