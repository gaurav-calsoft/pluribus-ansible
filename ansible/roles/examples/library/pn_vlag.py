#!/usr/bin/python
""" PN CLI vlag-create/vlag-delete/vlag-modify """

import subprocess
import shlex

DOCUMENTATION = """
---
module: pn_vlag
author: "Pluribus Networks"
short_description: CLI command to create/delete vlag.
description:
  - Execute vlag-create/vlag-delete/vlag-modify command.
  - A virtual link aggregation group (VLAG) allows links that are physically
    connected to two different Pluribus Networks devices to appear as a single
    trunk to a third device. The third device can be a switch, server, or any
    Ethernet device. A VLAG can provide Layer 2 multipathing, which allows you
    to create redundancy by increasing bandwidth, enabling multiple parallel
    paths between nodes and loadbalancing traffic where alternative paths exist.
options:
  pn_cliusername:
    description:
      - Login username
    required: true
    type: str
  pn_clipassword:
    description:
      - Login password
    required: true
    type: str
  pn_cliswitch:
    description:
      - Target switch to run this command on.
    type: str
  pn_command:
    description:
      - The C(pn_command) takes the vlag-create/delete/modify command as value.
    required: true
    choices: vlag-create, vlag-delete, vlag-modify
    type: str
  pn_name:
    description:
      - The C(pn_name) takes a valid name for vlag configuration.
    required: true
    type: str
  pn_port:
    description:
      - Specify the local VLAG port.
    required_if: vlag-create
    type: str
  pn_peer_port:
    description:
      - Specify the peer VLAG port.
    required_if: vlag-create
    type: str
  pn_mode:
    description:
      - Specify the mode for the VLAG. Active-standby indicates one side is
        active and the other side is in standby mode. Active-active indicates
        that both sides of the vlag are up by default.
    choices: active-active, active-standby
    type: str
  pn_peer_switch:
    description:
      - Specify the fabric-name of the peer switch.
    type: str
  pn_failover_action:
    description:
      - Specify the failover action as move or ignore.
    choices: move, ignore
    type: str
  pn_lacp_mode:
    description:
      - Specify the LACP mode.
    choices: off, passive, active
    type: str
  pn_lacp_timeout:
    description:
      - Specify the LACP timeout as slow(30 seconds) or fast(4 seconds).
    choices: slow, fast
    type: str
  pn_lacp_fallback:
    description:
      - Specify the LACP fallback mode as bundles or individual.
    choices: bundle, individual
    type: str
  pn_lacp_fallback_timeout:
    description:
      - Specify the LACP fallback timeout in seconds. The range is between 30
        and 60 seconds with a default value of 50 seconds.
    type: str
  pn_quiet:
    description:
      - Enable/disable the system information.
    required: false
    type: bool
    default: true
"""

EXAMPLES = """
- name: create a VLAG
  pn_vlag:
    pn_cliusername: admin
    pn_clipassword: admin
    pn_command: 'vlag-create'
    pn_name: spine-to-leaf
    pn_port: 'spine01-to-leaf'
    pn_peer_port: 'spine02-to-leaf'
    pn_peer_switch: spine02
    pn_mode: 'active-active'

- name: delete VLAGs
  pn_vlag:
    pn_cliusername: admin
    pn_clipassword: admin
    pn_command: 'vlag-delete'
    pn_name: spine-to-leaf
"""

RETURN = """
command:
  description: the CLI command run on the target node(s).
stdout:
  description: the set of responses from the vlag command.
  returned: always
  type: list
stderr:
  description: the set of error responses from the vlag command.
  returned: on error
  type: list
rc:
  description: return code of the module.
  returned: 0 on success, 1 on error
  type: int
changed:
  description: Indicates whether the CLI caused changes on the target.
  returned: always
  type: bool
"""


def main():
    """ This section is for argument parsing """
    module = AnsibleModule(
        argument_spec=dict(
            pn_cliusername=dict(required=True, type='str',
                                aliases=['username']),
            pn_clipassword=dict(required=True, type='str',
                                aliases=['password']),
            pn_cliswitch=dict(required=False, type='str', aliases=['switch']),
            pn_command=dict(required=True, type='str',
                            choices=['vlag-create', 'vlag-delete',
                                     'vlag-modify'], aliases=['command']),
            pn_name=dict(required=True, type='str', aliases=['name']),
            pn_port=dict(type='str', aliases=['port']),
            pn_peer_port=dict(type='str', aliases=['peer_port']),
            pn_mode=dict(type='str',
                         choices=['active-standby', 'active-active'],
                         aliases=['mode']),
            pn_peer_switch=dict(type='str', aliases=['peer_switch']),
            pn_failover_action=dict(type='str', choices=['move', 'ignore'],
                                    aliases=['failover_action']),
            pn_lacp_mode=dict(type='str', choices=['off', 'passive', 'active'],
                              aliases=['lacp_mode']),
            pn_lacp_timeout=dict(type='str', choices=['slow', 'fast'],
                                 aliases=['lacp_timeout']),
            pn_lacp_fallback=dict(type='str', choices=['individual', 'bundled'],
                                  aliases=['lacp_fallback']),
            pn_lacp_fallback_timeout=dict(type='str',
                                          aliases=['lacp_fallback_timeout']),
            pn_quiet=dict(default=True, type='bool')
        ),
        required_if=(
            ["pn_command", "vlag-create",
             ["pn_name", "pn_port", "pn_peer_port"]],
            ["pn_command", "vlag-delete", ["pn_name"]],
            ["pn_command", "vlag-modify", ["pn_name"]]
        )
    )

    # Argument accessing
    cliusername = module.params['pn_cliusername']
    clipassword = module.params['pn_clipassword']
    cliswitch = module.params['pn_cliswitch']
    command = module.params['pn_command']
    name = module.params['pn_name']
    port = module.params['pn_port']
    peer_port = module.params['pn_peer_port']
    mode = module.params['pn_mode']
    peer_switch = module.params['pn_peer_switch']
    failover_action = module.params['pn_failover_action']
    lacp_mode = module.params['pn_lacp_mode']
    lacp_timeout = module.params['pn_lacp_timeout']
    lacp_fallback = module.params['pn_lacp_fallback']
    lacp_fallback_timeout = module.params['pn_lacp_fallback_timeout']
    quiet = module.params['pn_quiet']

    # Building the CLI command string
    if quiet is True:
        cli = ('/usr/bin/cli --quiet --user ' + cliusername + ':' +
               clipassword + ' ')
    else:
        cli = '/usr/bin/cli --user ' + cliusername + ':' + clipassword + ' '

    if cliswitch:
        cli += ' switch ' + cliswitch

    cli += ' ' + command + ' name ' + name

    if port:
        cli += ' port ' + port

    if peer_port:
        cli += ' peer-port ' + peer_port

    if mode:
        cli += ' mode ' + mode

    if peer_switch:
        cli += ' peer-switch' + peer_switch

    if failover_action:
        cli += ' failover-' + failover_action + '-L2 '

    if lacp_mode:
        cli += ' lacp-mode ' + lacp_mode

    if lacp_timeout:
        cli += ' lacp-timeout ' + lacp_timeout

    if lacp_fallback:
        cli += ' lacp-fallback ' + lacp_fallback

    if lacp_fallback_timeout:
        cli += ' lacp-fallback-timeout ' + lacp_fallback_timeout

    # Run the CLI command
    vlagcmd = shlex.split(cli)
    response = subprocess.Popen(vlagcmd, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE, universal_newlines=True)

    # 'out' contains the output
    # 'err' contains the error messages
    out, err = response.communicate()

    # Response in JSON format
    if err:
        module.exit_json(
            command=cli,
            stderr=err.rstrip("\r\n"),
            rc=1,
            changed=False
        )

    else:
        module.exit_json(
            command=cli,
            stdout=out.rstrip("\r\n"),
            rc=0,
            changed=True
        )


# AnsibleModule boilerplate
from ansible.module_utils.basic import AnsibleModule

if __name__ == '__main__':
    main()