# Ansible Playbook For infrasim-compute

This playbook contains ansible tasks for infrasim installation and basic commands.

## Setup ansible and set ansible variables.

	sudo apt-get install ansible
    sudo apt-get install sshpass
    sudo apt-get install python-pip
    sudo pip install -U ansible
    export ANSIBLE_HOST_KEY_CHECKING=False

You can also edit /etc/ansible/ansible.cfg to uncomment **host_key_checking = False**.
Note that ansible 2.2.0.0+ is needed for running this playbook.

## Structure of this playbook

    group_vars/
        computes

    inventory_example

    roles/
        commoncmd/
            tasks/
                main.yml
        configcmd/
            tasks/
                main.yml
        installation/
            tasks/
                main.yml
        nodecmd/
            tasks/
                main.yml
        uninstallation/
            tasks/
                main.yml
    
    site.yml

**site.yml:** This is the master playbook, which contains two plays: Install InfraSIM and Manipulate InfraSIM.

**inventory_example:** This is an example of inventory file. You can add hosts under any child group.

	[quanta_d51]

	[quanta_t41]

	[dell_c6320]

	[dell_r630]

	[dell_r730]

	[dell_r730xd]

	[s2600kp]

	[s2600tp]

	[s2600wtt]

	[computes:children]
	quanta_d51
	quanta_t41
	dell_c6320
	dell_r630
	dell_r730
	dell_r730xd
	s2600kp
	s2600tp
	s2600wtt

	[computes:vars]
	ansible_connection=ssh
	ansible_user=infrasim
	ansible_port=22
    ansible_ssh_pass=infrasim

    ansible_become=true
    ansible_become_pass=infrasim
    ansible_become_flags= -S -n


After you add hosts under the type groups, you could specify **group name** when you execute ansible command, then only the hosts under this group will execute the command. E.g., when you run `ansible-playbook -i inventory_example -l s2600tp -t init`, only s2600tp hosts will run infrasim init task.

If you are not familiar with inventory file, you can refer to [Ansible Intro To Inventory](http://docs.ansible.com/ansible/intro_inventory.html).

**roles:** Several roles under the main playbook.

**group_vars:** Variables for inventory groups are defined under this directory. They will be overriden by command line variables.

## How to use ansible playbook to run specified task

    ansible-playbook -l <host pattern> -i <inventory_file> -t <tasktag> -e "variable1=xx variable2=xx" site.yml

Example:

    ansible-playbook -l quanta_d51 -i ./inventory_example -t nodestart  -e "node_name=default" site.yml

This means to start a vnode named **default** for quanta_d51 servers defined in "./inventory_example" inventory.
Note that:
-l limits hosts by specified pattern, if it's omitted, all hosts under [computes] group will execute the task.

## Provided tags for tasks and usage:

### Installation:

**install**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t install site.yml

Install infrasim on specified hosts.

### Uninstallation

**uninstall**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t uninstall site.yml

Uninstall infrasim from specified hosts.

### Common Commands:

**version**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t version site.yml

Check infrasim version on specified hosts.

**init**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t init site.yml

Init infrasim service on specified hosts.
After init, all your hosts are **quanta_d51**, you need to run **changetype** or **updateconfig** task to change the node type.

**help**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t help site.yml

List infrasim CLI command options.

### Config Commands:

**configlist**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t configlist site.yml

List mapped configurations for nodes in specified hosts.

**changetype**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t changetype site.yml -e "node_name=<node_name> node_type=<node_type>"

Change node type for node under specified hosts. If -e is not given, node_name=default, node_type=quanta_d51.

**delconfig**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t delconfig site.yml -e "node_name=<node_name>"

Delete node config of <node_name> in specified hosts.

**addconfig**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t addconfig site.yml -e "node_name=<node_name> yml_path=xxx.yml"

Add configuration mapping for <node_name> with yml file from **localhost**.
\<yml_path\> is mandatory.
    
**updateconfig**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t addconfig site.yml -e "node_name=<node_name> yml_path=xxx.yml"

Update configuration mapping for <node_name> with yml file from **localhost**.
\<yml_path\> is mandatory.

### Node Commands

**nodestart**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t nodestart site.yml -e "node_name=<node_name>"

Start node <node_name> on specified hosts.

**nodestop**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t nodestop site.yml -e "node_name=<node_name>"

Stop node <node_name> on specified hosts.

**noderestart**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t noderestart site.yml -e "node_name=<node_name>"

Restart node <node_name> on specified hosts.

**nodedestroy**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t nodedestroy site.yml -e "node_name=<node_name>"

Stop node <node_name> and tear down its runtime workspace on specified hosts.

**nodestatus**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t nodestatus site.yml -e "node_name=<node_name>"

Check node <node_name>'s running status on specified hosts.

**nodeinfo**

    ansible-playbook -l <host_pattern> -i <inventory_file> -t nodeinfo site.yml -e "node_name=<node_name>"

Check node <node_name>'s specification on specified hosts.
