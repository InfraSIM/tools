#!/usr/bin/python
"""
this file is used to generate fru data
"""
__author__ = 'payne'

import os
import sys
import subprocess
import argparse
import time


def param_parse():
    """
    handle users' inputs
    """
    parser = argparse.ArgumentParser(description="the arguments for fru data generate")
    parser.add_argument("--ip", required=True, action="store",
                        help="the BMC ip address of physical server")
    parser.add_argument("-U", "--user", required=True, action="store",
                        help="the username of physical server")
    parser.add_argument("-P", "--pwd", required=True, action="store",
                        help="the password of physical server")
    parser.add_argument("--id", required=False, action="store",
                        help="the id of the fru to be generated "
                             "all of fru will be covered if not given")
    parser.add_argument("-D", "--folder", required=False, default="",
                        action="store",
                        help="the path where to store the result file "
                             "a new folder named fru is created if not given")
    parser.add_argument("-S", "--source", required=False, default="/usr/bin/",
                        action="store",
                        help="the path where ipmitool is installed "
                             "user can select the specific verion of this tool")
    args = parser.parse_args()
    return args


def run_command(cmd="", shell=True, stdout=None, stderr=None, *args, **kwargs):
    """
    :param cmd: the command should run
    :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
    :param stdout: reference subprocess module
    :param stderr: reference subprocess module
    :return: tuple (return code, info)
    """
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_returncode = child.returncode
    if cmd_returncode != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


def file_generate(user_data):
    if not os.path.isdir(user_data.folder):
        new_folder = time.strftime("%Y%m%d%H%M%S", time.localtime())
        print "create new folder named {} in current working path".format(new_folder)
        os.mkdir(new_folder)
        user_data.folder = "./{}".format(new_folder)
    ipmitool_cmd = "{SOURCE} -H {IP} -I lanplus -U {USER} -P {PWD} ".format(
        SOURCE=os.path.join(user_data.source, "ipmitool"),
        IP=user_data.ip,
        USER=user_data.user,
        PWD=user_data.pwd)
    if not user_data.id:
        print "user doesn't provide FRU ID, will cover all"
        ipmitool_get_id_cmd = '{} fru list | grep "FRU Device Description : " | ' \
                              'sed "s/\(.*\)ID \(.*\))/\\2/g"'.format(ipmitool_cmd)
        returncode, cmd_result = run_command(ipmitool_get_id_cmd,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
        if returncode == 0:
            user_data.id = cmd_result.strip().split(os.linesep)
        else:
            print "can't get the fru ID"
            sys.exit(1)
    else:
        user_data.id = user_data.id.strip().split()

    for fru_id in user_data.id:
        bin_file = "fru{}.bin".format(fru_id)
        ipmitool_fru_read_cmd = "{ipmitool_cmd} fru read {ID} {file_name}".\
            format(ipmitool_cmd=ipmitool_cmd, ID=fru_id,
                   file_name=os.path.join(user_data.folder, bin_file))
        returncode, cmd_result = run_command(ipmitool_fru_read_cmd,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
        if returncode != 0:
            print "can't read the fru {} data".format(fru_id)
            sys.exit(1)

    return user_data.folder


def file_handle(fru_folder, fru_file):
    special = False
    new_file = ""
    last_line = ""
    print "hexdump {} > tmp".format(os.path.join(fru_folder, fru_file))
    run_command("hexdump {} > tmp".format(os.path.join(fru_folder, fru_file)))
    with open("./tmp") as file:
        for line in file.readlines():
            if special:
                cur = line.split(' ', 1)
                pre = last_line.split(' ', 1)
                line_num = int("0x{}".format(cur[0]), base=16) - int("0x{}".format(pre[0]), base=16)
                line_num = line_num/16-1
                for i in range(line_num):
                    new_file += pre[1]
                if len(cur) == 2:
                    new_file += cur[1]
                    special = False
                    last_line = line
                    continue
                else:
                    return new_file
            if "*" in line:
                special = True
            else:
                try:
                    new_file += line.split(' ', 1)[1]
                except IndexError:
                    print "the file is handled completely"
                    return new_file  # normally at the end of this file
                else:
                    last_line = line


def data_handle(new_file):
    new_data = ""
    print "start to handle data"
    for line in new_file.split(os.linesep):
        if not line:
            continue
        content = line.split()
        if len(content) != 8:
            print "error"
            print content
            sys.exit(1)
        for i in range(4):
            data = content[i]
            new_data += "0x{} 0x{} ".format(data[2:4], data[0:2])
        new_data += "\\"+os.linesep
        for i in range(4, 8):
            data = content[i]
            new_data += "0x{} 0x{} ".format(data[2:4], data[0:2])
        new_data += "\\"+os.linesep
    return new_data


def store_result(new_data, fru_folder, fru_file):
    print "start to save result file"
    fru_result = "result_{}".format(fru_file)
    with open("{}".format(os.path.join(fru_folder, fru_result)), "w") as result_file:
        result_file.write(new_data)


def main():
    args = param_parse()
    fru_folder = file_generate(args)
    for root, fru_dir, fru_flies in os.walk(fru_folder):
        for fru_file in fru_flies:
            new_file = file_handle(fru_folder, fru_file)
            new_data = data_handle(new_file)
            store_result(new_data, fru_folder, fru_file)
    os.remove("./tmp")


if __name__ == "__main__":
    main()

