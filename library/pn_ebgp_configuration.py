#!/usr/bin/python
""" PN eBGP Configuration """

#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import shlex

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: pn_ebgp_configuration
author: 'Pluribus Networks (devops@pluribusnetworks.com)'
description: Module to configure eBGP.
eBGP csv file format: l3_port, interface_ip, bgp_as, neighbor_ip, remote_as
options:
    pn_cliusername:
      description:
        - Provide login username if user is not root.
      required: False
      type: str
    pn_clipassword:
      description:
        - Provide login password if user is not root.
      required: False
      type: str
    pn_switch:
      description:
        - Name of the switch on which this task is currently getting executed.
      required: True
      type: str
    pn_bgp_data:
      description:
        - String containing trunk data parsed from csv file.
      required: False
      type: str
      default: ''
"""

EXAMPLES = """
- name: Configure eBGP
  pn_ebgp_creation:
    pn_cliusername: "{{ USERNAME }}"
    pn_clipassword: "{{ PASSWORD }}"
    pn_switch: "{{ inventory_hostname }}"
    pn_bgp_data: "{{ lookup('file', '{{ bgp_file }}') }}"
"""

RETURN = """
summary:
  description: It contains output of each configuration along with switch name.
  returned: always
  type: str
changed:
  description: Indicates whether the CLI caused changes on the target.
  returned: always
  type: bool
unreachable:
  description: Indicates whether switch was unreachable to connect.
  returned: always
  type: bool
failed:
  description: Indicates whether or not the execution failed on the target.
  returned: always
  type: bool
exception:
  description: Describes error/exception occurred while executing CLI command.
  returned: always
  type: str
task:
  description: Name of the task getting executed on switch.
  returned: always
  type: str
msg:
  description: Indicates whether configuration made was successful or failed.
  returned: always
  type: str
"""

CHANGED_FLAG = []


def pn_cli(module):
    """
    Generate the cli portion to launch the Netvisor cli.
    :param module: The Ansible module to fetch username and password.
    :return: The cli string for further processing.
    """
    username = module.params['pn_cliusername']
    password = module.params['pn_clipassword']

    if username and password:
        cli = '/usr/bin/cli --quiet --user %s:%s ' % (username, password)
    else:
        cli = '/usr/bin/cli --quiet '

    return cli


def run_cli(module, cli):
    """
    Execute the cli command on the target node(s) and returns the output.
    :param module: The Ansible module to fetch input parameters.
    :param cli: The complete cli string to be executed on the target node(s).
    :return: Output or Error msg depending upon the response from cli else None.
    """
    results = []
    cli = shlex.split(cli)
    rc, out, err = module.run_command(cli)

    if out:
        return out
    if err:
        json_msg = {
            'switch': module.params['pn_switch'],
            'output': u'Operation Failed: {}'.format(' '.join(cli))
        }
        results.append(json_msg)
        module.exit_json(
            unreachable=False,
            failed=True,
            exception=err.strip(),
            summary=results,
            task='Configure eBGP',
            msg='eBGP configuration failed',
            changed=False
        )
    else:
        return 'Success'


def create_vrouter(module, vrouter_name, vnet_name):
    """
    Create a hardware vrouter using vrrp id.
    :param module: The Ansible module to fetch input parameters.
    :param vrouter_name: Name of the vrouter to create.
    :param vnet_name: Vnet name required for vrouter creation.
    :return: String describing if vrouter got created or not.
    """
    global CHANGED_FLAG
    output = ''
    new_vrouter = False

    # Check if vrouter already exists
    cli = pn_cli(module)
    cli += ' vrouter-show format name no-show-headers '
    existing_vrouter_names = run_cli(module, cli)

    if existing_vrouter_names is not None:
        existing_vrouter_names = existing_vrouter_names.split()
        if vrouter_name not in existing_vrouter_names:
            new_vrouter = True

    if new_vrouter or existing_vrouter_names is None:
        cli = pn_cli(module)
        cli += ' vrouter-create name %s ' % vrouter_name
        cli += ' vnet %s enable ' % (vnet_name)
        cli += ' router-type hardware '
        run_cli(module, cli)
        CHANGED_FLAG.append(True)
        output += 'Created vrouter with name %s\n' % vrouter_name

    return output


def vrouter_interface_bgp_add(module, switch_name, l3_port, interface_ip, neighbor_ip,
                               remote_as):
    """
    Method to create interfaces and add ibgp neighbors.
    :param module: The Ansible module to fetch input parameters.
    :param switch_name: The name of the switch to run interface.
    :param interface_ip: Interface ip to create a vrouter interface.
    :param neighbor_ip: Neighbor_ip for the ibgp neighbor.
    :param remote_as: Bgp-as for remote switch.
    :return: String describing if ibgp neighbours got added or already exists.
    """
    global CHANGED_FLAG
    output = ''
    cli = pn_cli(module)
    clicopy = cli

    cli = clicopy
    cli += ' vrouter-show location %s format name' % switch_name
    cli += ' no-show-headers'
    vrouter = run_cli(module, cli).split()[0]

    cli = clicopy
    cli += ' vrouter-interface-show ip %s l3-port %s' % (interface_ip, l3_port)
    cli += ' format switch no-show-headers'
    existing_vrouter_interface = run_cli(module, cli).split()

    if vrouter not in existing_vrouter_interface:
        cli = clicopy
        cli += ' vrouter-interface-add vrouter-name %s ip %s l3-port %s ' % (
            vrouter, interface_ip, l3_port
        )
        run_cli(module, cli)

        output += ' Added vrouter interface with ip %s on %s \n' % (
            interface_ip, vrouter
        )
        CHANGED_FLAG.append(True)

    neighbor_ip = neighbor_ip.split('/')[0]
    cli = clicopy
    cli += ' vrouter-bgp-show remote-as ' + remote_as
    cli += ' neighbor %s format switch no-show-headers' % neighbor_ip
    already_added = run_cli(module, cli).split()

    if vrouter not in already_added:
        cli = clicopy
        cli += ' vrouter-bgp-add vrouter-name %s' % vrouter
        cli += ' neighbor %s remote-as %s' % (neighbor_ip,
                                                            remote_as)

        if 'Success' in run_cli(module, cli):
            output += ' Added BGP neighbor %s for %s \n' % (neighbor_ip,
                                                                 vrouter)
            CHANGED_FLAG.append(True)

    return output


def modify_auto_trunk_setting(module, switch, flag):
    """
    Method to enable/disable auto trunk setting of a switch.
    :param module: The Ansible module to fetch input parameters.
    :param switch: Name of the local switch.
    :param flag: Enable/disable flag for the cli command.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    if flag.lower() == 'enable':
        cli += ' switch %s system-settings-modify auto-trunk ' % switch
        return run_cli(module, cli)
    elif flag.lower() == 'disable':
        cli += ' switch %s system-settings-modify no-auto-trunk ' % switch
        return run_cli(module, cli)


def delete_trunk(module, switch, switch_port):
    """
    Method to delete a conflicting trunk on a switch.
    :param module: The Ansible module to fetch input parameters.
    :param switch: Name of the local switch.
    :param switch_port: The l3-port which is part of conflicting trunk for l3.
    :param peer_switch: Name of the peer switch.
    :return: String describing if trunk got deleted or not.
    """
    cli = pn_cli(module)
    clicopy = cli

    cli += ' switch %s trunk-show ports %s ' % (switch, switch_port)
    cli += ' format name no-show-headers '
    trunk = run_cli(module, cli).split()
    trunk = list(set(trunk))
    if 'Success' not in trunk and len(trunk) > 0:
        cli = clicopy
        cli += ' switch %s trunk-delete name %s ' % (switch, trunk[0])
        if 'Success' in run_cli(module, cli):
            CHANGED_FLAG.append(True)
            return ' Deleted %s trunk successfully \n' % (trunk[0])


def bgp_configuration(module):
    output = ''
    cli = pn_cli(module)
    clicopy = cli
    switch = module.params['pn_switch']
    vrouter_name = switch + '-vrouter'

    cli = clicopy
    cli += ' fabric-node-show format fab-name no-show-headers '
    fabric_name = list(set(run_cli(module, cli).split()))[0]

    # Create vrouter
    vnet_name = fabric_name + '-global'
    output += create_vrouter(module, vrouter_name, vnet_name)

    # Disable auto trunk on all switches.
    modify_auto_trunk_setting(module, switch, 'disable')

    bgp_data = module.params['pn_bgp_data']
    if bgp_data:
        bgp_data = bgp_data.replace(' ', '')
        bgp_data_list = bgp_data.split('\n')
        for row in bgp_data_list:
            if row.startswith('#'):
                continue
            else:
                elements = row.split(',')
                l3_port = elements.pop(0)
                interface_ip = elements.pop(0)
                bgp_as = elements.pop(0)
                neighbor_ip = elements.pop(0)
                remote_as = elements.pop(0)

    cli = clicopy
    cli += ' vrouter-modify name %s ' % vrouter_name
    cli += ' bgp-as %s ' % bgp_as
    if 'Success' in run_cli(module, cli):
        output += ' Added bgp_as %s \n' % (bgp_as)

    delete_trunk(module, switch, l3_port)
    output += vrouter_interface_bgp_add(module, switch, l3_port, interface_ip, neighbor_ip, remote_as)

    return output


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            pn_cliusername=dict(required=False, type='str'),
            pn_clipassword=dict(required=False, type='str', no_log=True),
            pn_switch=dict(required=True, type='str'),
            pn_bgp_data=dict(required=False, type='str', default=''),
        )
    )

    global CHANGED_FLAG
    results = []
    message = ''

    bgp_data = module.params['pn_bgp_data']

    message += bgp_configuration(module)

    for line in message.splitlines():
        if line:
            results.append({
                'switch': module.params['pn_switch'],
                'output': line
            })

    # Exit the module and return the required JSON.
    module.exit_json(
        unreachable=False,
        msg='eBGP configuration succeeded',
        summary=results,
        exception='',
        failed=False,
        changed=True if True in CHANGED_FLAG else False,
        task='Configure eBGP'
    )

if __name__ == '__main__':
    main()
