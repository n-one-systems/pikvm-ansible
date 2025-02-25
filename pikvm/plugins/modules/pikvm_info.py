#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_info
short_description: Retrieve information from a PiKVM device
description:
  - This module retrieves system information from a PiKVM device.
  - The returned information includes hardware details, software versions, and system state.
version_added: "1.0.0"
author:
  - "Your Name (@yourgithub)"
options:
  hostname:
    description:
      - The hostname or IP address of the PiKVM device.
    type: str
    required: true
  username:
    description:
      - The username to authenticate with the PiKVM device.
    type: str
    required: true
  password:
    description:
      - The password to authenticate with the PiKVM device.
    type: str
    required: true
  secret:
    description:
      - The TOTP secret for two-factor authentication.
      - Can be found in /etc/kvmd/totp.secret on the PiKVM device.
    type: str
    required: false
  use_https:
    description:
      - Whether to use HTTPS for API requests.
    type: bool
    default: true
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: false
  fields:
    description:
      - List of information categories to retrieve.
      - If not specified, all categories will be returned.
      - Valid options include system, hw, streamer, and more.
    type: list
    elements: str
    required: false
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module supports check mode.
'''

EXAMPLES = r'''
- name: Get all system information
  nsys.pikvm.pikvm_info:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
  register: pikvm_info

- name: Get only system and hardware information
  nsys.pikvm.pikvm_info:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    fields:
      - system
      - hw
  register: pikvm_system_info

- name: Connect with 2FA
  nsys.pikvm.pikvm_info:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    secret: "3OBBOGSJRYRBZH35PGXURM4CMWTH3WSU"
  register: pikvm_info
'''

RETURN = r'''
info:
  description: The PiKVM system information.
  returned: success
  type: dict
  contains:
    system:
      description: General system information.
      type: dict
      returned: always
      sample: {"version": {"platform": "v2-hdmi-rpi4", "os": "Linux ARM 5.15.0-1030-raspi (Ubuntu 22.04)", "cdrom": "0.96"}}
    hw:
      description: Hardware information.
      type: dict
      returned: always
      sample: {"health": {"throttling": {"raw_bits": 0, "undervoltage": {"now": false, "past": false}}}}
    atx:
      description: ATX power management information.
      type: dict
      returned: when available
      sample: {"enabled": true, "busy": false, "leds": {"power": true, "hdd": false}}
    msd:
      description: Mass Storage Device information.
      type: dict
      returned: when available
      sample: {"enabled": true, "connected": false, "image": null, "drive": {"image": null, "cdrom": true, "rw": false}}
    gpio:
      description: GPIO state information.
      type: dict
      returned: when available
    streamer:
      description: Video streamer information.
      type: dict
      returned: when available
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    create_module,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
    update_result,
)


def main():
    # Define additional arguments for this module
    argument_spec = dict(
        fields=dict(type='list', elements='str', required=False)
    )
    
    # Create the module
    module = create_module(argument_spec=argument_spec)
    
    # Initialize result
    result = dict(
        changed=False,
        info={}
    )
    
    # Get fields param if specified
    fields = module.params.get('fields')
    
    # Skip execution in check mode
    if module.check_mode:
        module.exit_json(**result)
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Execute API call
        system_info = execute_pikvm_module(
            module, client, result,
            client.get_system_info,
            fields=fields
        )
        
        # Store result
        if system_info:
            result['info'] = system_info.get('result', {})
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to retrieve PiKVM information: {str(e)}")


if __name__ == '__main__':
    main()
