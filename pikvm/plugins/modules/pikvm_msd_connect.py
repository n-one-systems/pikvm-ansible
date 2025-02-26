#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_msd_connect
short_description: Connect or disconnect PiKVM Mass Storage Device (MSD)
description:
  - This module connects or disconnects a PiKVM Mass Storage Device (MSD) to/from the target server.
  - It can also verify the connection state before making changes.
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
  state:
    description:
      - The desired connection state of the MSD.
      - connected - Connect the MSD to the server.
      - disconnected - Disconnect the MSD from the server.
    type: str
    choices: ['connected', 'disconnected']
    required: true
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module supports check mode.
  - Connection/disconnection is only possible when an image is selected in the MSD.
'''

EXAMPLES = r'''
- name: Connect MSD to the server
  nsys.pikvm.pikvm_msd_connect:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: connected

- name: Disconnect MSD from the server
  nsys.pikvm.pikvm_msd_connect:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: disconnected
'''

RETURN = r'''
msd_state:
  description: The MSD state information after the operation.
  returned: success
  type: dict
  contains:
    enabled:
      description: Whether the MSD is enabled.
      type: bool
      sample: true
    connected:
      description: Whether the MSD is connected to the server.
      type: bool
      sample: true
    image:
      description: The name of the currently selected image.
      type: str
      sample: "ubuntu.iso"
    drive:
      description: Drive configuration details.
      type: dict
      sample: {"image": "ubuntu.iso", "cdrom": true, "rw": false}
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    create_module,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
    update_result,
    has_diff,
    get_diff,
)


def main():
    # Define additional arguments for this module
    argument_spec = dict(
        state=dict(type='str', required=True, choices=['connected', 'disconnected']),
    )
    
    # Create the module
    module = create_module(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    
    # Initialize result
    result = dict(
        changed=False,
    )
    
    # Get parameters
    desired_state = module.params.get('state')
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Get current MSD state
        msd_state = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        current_state = msd_state.get('result', {})
        result['msd_state'] = current_state
        
        # Determine if MSD is currently connected
        is_connected = current_state.get('connected', False)
        
        # Determine if we need to change the state
        needs_change = False
        if desired_state == 'connected' and not is_connected:
            needs_change = True
        elif desired_state == 'disconnected' and is_connected:
            needs_change = True
        
        # Check if an image is selected
        current_image = current_state.get('drive', {}).get('image')
        if needs_change and not current_image:
            module.fail_json(msg="No image is currently selected in the MSD. Select an image before connecting/disconnecting.")
        
        # Store the before state for diff
        before = {'connected': is_connected}
        
        # Make the change if needed and not in check mode
        if needs_change and not module.check_mode:
            connected_value = True if desired_state == 'connected' else False
            
            execute_pikvm_module(
                module, client, result,
                client.connect_msd,
                connected=connected_value
            )
            
            # Get updated state
            updated_msd_state = execute_pikvm_module(
                module, client, result,
                client.get_msd_state
            )
            
            updated_state = updated_msd_state.get('result', {})
            result['msd_state'] = updated_state
        
        # Store the after state for diff
        after = {'connected': True if desired_state == 'connected' else False}
        
        # Add diff to result
        if needs_change:
            result['diff'] = get_diff(before, after)
            result['changed'] = True
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to change MSD connection state: {str(e)}")


if __name__ == '__main__':
    main()
