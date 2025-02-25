#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_facts
short_description: Gather facts from PiKVM devices
description:
  - This module gathers facts from PiKVM devices.
  - The gathered facts will be added to the ansible_facts.pikvm namespace.
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
  gather_subset:
    description:
      - If supplied, restrict the facts returned to the given subset.
      - Possible values are all, system, hardware, atx, msd, gpio, streamer.
    type: list
    elements: str
    default: [ 'all' ]
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
'''

EXAMPLES = r'''
- name: Gather all PiKVM facts
  nsys.pikvm.pikvm_facts:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"

- name: Gather only system and hardware facts
  nsys.pikvm.pikvm_facts:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    gather_subset:
      - system
      - hardware

- name: Use in a task with the gathered facts
  debug:
    msg: "PiKVM version is {{ ansible_facts.pikvm.system.version.platform }}"
  when: ansible_facts.pikvm is defined
'''

RETURN = r'''
ansible_facts:
  description: Facts to add to ansible_facts.
  returned: always
  type: dict
  contains:
    pikvm:
      description: PiKVM facts gathered
      type: dict
      returned: always
      contains:
        system:
          description: General system information.
          type: dict
          returned: when subset includes 'system' or 'all'
        hardware:
          description: Hardware information.
          type: dict
          returned: when subset includes 'hardware' or 'all'
        atx:
          description: ATX power management information.
          type: dict
          returned: when subset includes 'atx' or 'all'
        msd:
          description: Mass Storage Device information.
          type: dict
          returned: when subset includes 'msd' or 'all'
        gpio:
          description: GPIO state information.
          type: dict
          returned: when subset includes 'gpio' or 'all'
        streamer:
          description: Video streamer information.
          type: dict
          returned: when subset includes 'streamer' or 'all'
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    pikvm_argument_spec,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
)


def map_subset_to_fields(subset):
    """
    Map Ansible subset names to PiKVM API field names
    """
    mapping = {
        'system': 'system',
        'hardware': 'hw',
        'atx': 'atx',
        'msd': 'msd',
        'gpio': 'gpio',
        'streamer': 'streamer'
    }
    
    if 'all' in subset:
        return None  # API returns all fields when no specific fields are requested
        
    return [mapping.get(item, item) for item in subset if item in mapping]


def main():
    # Define additional arguments for this module
    argument_spec = pikvm_argument_spec()
    argument_spec.update(
        gather_subset=dict(
            type='list',
            elements='str',
            default=['all'],
            options=[
                'all',
                'system',
                'hardware',
                'atx',
                'msd',
                'gpio',
                'streamer'
            ]
        )
    )
    
    # Create the module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )
    
    # Initialize result with empty ansible_facts
    result = dict(
        ansible_facts=dict(
            pikvm=dict()
        ),
        changed=False
    )
    
    # Get gather_subset param
    gather_subset = module.params.get('gather_subset', ['all'])
    
    # Map subset names to API field names
    fields = map_subset_to_fields(gather_subset)
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Execute API call
        system_info = execute_pikvm_module(
            module, client, result,
            client.get_system_info,
            fields=fields
        )
        
        # Process and rename fields for better Ansible compatibility
        pikvm_facts = {}
        
        if system_info and 'result' in system_info:
            info = system_info['result']
            
            # Map hw to hardware for better naming
            if 'hw' in info:
                pikvm_facts['hardware'] = info.pop('hw')
                
            # Add remaining fields
            for key, value in info.items():
                pikvm_facts[key] = value
        
        # Add to ansible_facts
        result['ansible_facts']['pikvm'] = pikvm_facts
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to retrieve PiKVM facts: {str(e)}")


if __name__ == '__main__':
    main()
