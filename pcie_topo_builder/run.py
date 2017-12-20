#!/usr/bin/env python

import paramiko
import subprocess
from time import sleep
import argparse
import os

def parse_args():
    description = "usage: generate yaml file with pcie topology"
    parser = argparse.ArgumentParser(description = description)

    help = "jump server ip:user:password"
    parser.add_argument('-J', '--jump_server', type=str, help=help)

    help = "server ip:user:password"
    parser.add_argument('-S', '--server', type=str, help=help)

    help = "path to store tar in server"
    parser.add_argument('-P', '--tar_path', type=str, help=help, default='/tmp')

    help = '[Add or Replace] which element to be copied from source yaml to target yaml'
    parser.add_argument('-E', '--insert_element', nargs='+', type=str, help=help)

    help = '[Merge] which element to be copied from source yaml to target yaml'
    parser.add_argument('-M', '--merge_element', nargs='+', type=str, help=help)

    args = parser.parse_args();
    return args

def printlines(info):
    for line in info:
        print line

def execute_command_server(cmd_list):
    for cmd in cmd_list:
        print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
        print cmd
        pd = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        printlines(pd.stdout.readlines())
        printlines(pd.stderr.readlines())
        error = pd.stderr.readlines()
        if error:
            print 'Failed!'
            printlines(error)
            exit()

def execute_command_jump(cmd_list, ssh):
    for cmd in cmd_list:
        print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
        print cmd
        stdin, stdout, stderr = ssh.exec_command(cmd)
        error = stderr.readlines()
        if error:
            print 'Failed!'
            printlines(error)
            exit()

def execute_command(parms):
    jump_server = parms.jump_server
    if jump_server:
        jump_ip, jump_user, jump_pw = jump_server.split(':')
    server = parms.server
    try:
        server_ip, server_user, server_pw = server.split(':')
    except AttributeError as e:
        print ('Error: No server info !!!')
        exit()
    tar_path = parms.tar_path

    cmd_list = []
    tar_path_2 = os.path.join(tar_path, 'pcie_topo.tar')
    excute_path = os.path.join(tar_path, 'pcie_topo/pcie_topo')
    file_path = os.path.join(tar_path, 'pcie_topo/')
    yaml_path = os.path.join(file_path, 'topology.yml')

    if jump_server:
        print "copy pcie_topo.tar to jump server\n"
        print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
        cmd = 'sshpass -p {} scp -o StrictHostKeyChecking=no pcie_topo.tar {}@{}:/home/{}/pcie_topo.tar'.format(jump_pw,
                                                                                    jump_user,
                                                                                    jump_ip,
                                                                                    jump_user)
        execute_command_server([cmd])

        cmd_list.append('sshpass -p {} scp -o StrictHostKeyChecking=no /home/{}/pcie_topo.tar {}@{}:/tmp/pcie_topo.tar'.format(server_pw,
                                                                                                    jump_user,
                                                                                                    server_user,
                                                                                                    server_ip))
        cmd_list.append('sshpass -p {} ssh -o StrictHostKeyChecking=no {}@{} tar -xf {} -C {}'.format(server_pw,
                                                                           server_user,
                                                                           server_ip,
                                                                           tar_path_2,
                                                                           tar_path))
        cmd_list.append('sshpass -p {} ssh -o StrictHostKeyChecking=no {}@{} {} --file_path={}'.format(server_pw,
                                                                            server_user,
                                                                            server_ip,
                                                                            excute_path,
                                                                            file_path))
        cmd_list.append('sshpass -p {} scp -o StrictHostKeyChecking=no {}@{}:{} /home/{}/topology.yml'.format(server_pw,
                                                                                   server_user,
                                                                                   server_ip,
                                                                                   yaml_path,
                                                                                   jump_user))

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=jump_ip, port=22, username=jump_user, password=jump_pw)

        execute_command_jump(cmd_list, ssh)
        ssh.close()

        cmd_insert = 'sshpass -p {} scp -o StrictHostKeyChecking=no {}@{}:/home/{}/topology.yml topology.yml'.format(jump_pw,
                                                                                         jump_user,
                                                                                         jump_ip,
                                                                                         jump_user)
        execute_command_server([cmd_insert])

    else:
        cmd_list.append('sshpass -p {} scp -o StrictHostKeyChecking=no pcie_topo.tar {}@{}:{}'.format(server_pw,
                                                                      server_user,
                                                                      server_ip,
                                                                      tar_path))

        cmd_list.append('sshpass -p {} ssh -o StrictHostKeyChecking=no {}@{} tar -xf {} -C {}'.format(server_pw,
                                                                          server_user,
                                                                          server_ip,
                                                                          tar_path_2,
                                                                          tar_path))
        cmd_list.append('sshpass -p {} ssh -o StrictHostKeyChecking=no {}@{} {} --file_path={}'.format(server_pw,
                                                                           server_user,
                                                                           server_ip,
                                                                           excute_path,
                                                                           file_path))
        cmd_list.append('sshpass -p {} scp -o StrictHostKeyChecking=no {}@{}:{} topology.yml'.format(server_pw,
                                                                         server_user,
                                                                         server_ip,
                                                                         yaml_path))
        execute_command_server(cmd_list)

def main():
    print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
    print "clean environment\n"
    print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
    parms = parse_args()

    cmd_clean = 'rm -rf pcie_topo.tar toplogy.yml dist/ build/ output.yml'
    p = subprocess.Popen(cmd_clean, shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)

    print "pyinstaller\n"
    print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
    cmd_install = 'pyinstaller pcie_topo.py --add-data id_table.json:./'
    p = subprocess.Popen(cmd_install, shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    if "error" in p.stderr.readlines():
        print 'pyinstaller failed!'
        exit()

    cmd_tar = 'tar -cf pcie_topo.tar -C dist/ pcie_topo'
    p = subprocess.Popen(cmd_tar, shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    if p.stderr.readlines():
        print 'tar -cf failed!'
        exit()

    execute_command(parms)

    print "insert topology.yml to target infrasim.yml\n"
    print "+++++++++++++++++++++++++++++++++++++++++++++++++++\n"
    merge_element_list = parms.merge_element
    insert_element_list = parms.insert_element
    insert_element_str = ''
    merge_element_str = ''

    if insert_element_list:
        insert_element_str = ' -E {}'.format(' '.join(insert_element_list))
    if merge_element_list:
        merge_element_str = ' -M {}'.format(' '.join(merge_element_list))

    cmd_insert = './insert_yaml.py -S topology.yml' \
                    ' -T infrasim.yml -O output.yml {}'.format(
                                                    insert_element_str,
                                                    merge_element_str)
    p = subprocess.Popen(cmd_insert, shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    error = p.stderr.readlines()
    if error:
        print 'insert_yaml failed!'
        printlines(error)
        exit()

    print "Done"

if __name__ == '__main__':
    main()
