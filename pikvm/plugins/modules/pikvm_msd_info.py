#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_msd_info
short_description: Retrieve information about PiKVM Mass Storage Device (MSD)
description:
  - This module retrieves detailed information about the PiKVM Mass Storage Device (MSD).
  - It includes information about available images, connection status, and drive parameters.
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
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module supports check mode.
'''

EXAMPLES = r'''
- name: Get MSD information
  nsys.pikvm.pikvm_msd_info:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
  register: msd_info

- name: Display current MSD state
  debug:
    var: msd_info

- name: Check if MSD is connected
  debug:
    msg: "MSD is currently connected to the server"
  when: msd_info.connected

- name: List available images
  debug:
    msg: "Available images: {{ msd_info.images | join(', ') }}"
'''

RETURN = r'''
enabled:
  description: Whether the MSD is enabled.
  returned: success
  type: bool
  sample: true
connected:
  description: Whether the MSD is connected to the server.
  returned: success
  type: bool
  sample: true
busy:
  description: Whether the MSD is currently busy.
  returned: success
  type: bool
  sample: false
current_image:
  description: The name of the currently selected image.
  returned: success
  type: str
  sample: "ubuntu.iso"
is_cdrom:
  description: Whether the MSD is configured as a CD-ROM.
  returned: success
  type: bool
  sample: true
is_rw:
  description: Whether the MSD is configured as read-write.
  returned: success
  type: bool
  sample: false
images:
  description: List of available image names.
  returned: success
  type: list
  elements: str
  sample: ["ubuntu.iso", "data.img"]
images_info:
  description: Detailed information about each available image.
  returned: success
  type: dict
  sample: {
    "ubuntu.iso": {
      "size": 1073741824,
      "mtime": 1623456789
    }
  }
raw:
  description: The raw MSD state information from the PiKVM API.
  returned: success
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    create_module,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
)


def main():
    # Create the module
    module = create_module(
        supports_check_mode=True,
    )
    
    # Initialize result
    result = dict(
        changed=False,
    )
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Get MSD state
        msd_state = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        current_state = msd_state.get('result', {})
        
        # Store raw data
        result['raw'] = current_state
        
        # Extract useful information
        result['enabled'] = current_state.get('enabled', False)
        result['connected'] = current_state.get('connected', False)
        result['busy'] = current_state.get('busy', False)
        
        # Get drive information
        drive = current_state.get('drive', {})
        result['current_image'] = drive.get('image')
        result['is_cdrom'] = drive.get('cdrom', True)
        result['is_rw'] = drive.get('rw', False)
        
        # Get images information
        images_info = current_state.get('images', {})
        result['images'] = list(images_info.keys())
        result['images_info'] = images_info
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to retrieve MSD information: {str(e)}")


if __name__ == '__main__':
    main()
