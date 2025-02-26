#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_msd_params
short_description: Configure PiKVM Mass Storage Device (MSD) parameters
description:
  - This module configures parameters for a PiKVM Mass Storage Device (MSD).
  - It can select which image to use, set the device mode (CD-ROM/flash), and read-write permissions.
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
  image:
    description:
      - The name of the image to select for the MSD.
      - This must be an image that has already been uploaded to the PiKVM.
    type: str
    required: true
  cdrom:
    description:
      - Whether to configure the MSD as a CD-ROM.
      - If false, configures as a flash drive.
    type: bool
    default: true
  rw:
    description:
      - Whether to make the MSD read-write.
      - If false, makes the MSD read-only.
      - Ignored when cdrom=true (CD-ROMs are always read-only).
    type: bool
    default: false
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module supports check mode.
  - If the MSD is currently connected, you may need to disconnect it first before changing parameters.
'''

EXAMPLES = r'''
- name: Set ISO image as CD-ROM
  nsys.pikvm.pikvm_msd_params:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    image: "ubuntu.iso"
    cdrom: true

- name: Set image as writable flash drive
  nsys.pikvm.pikvm_msd_params:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    image: "data.img"
    cdrom: false
    rw: true
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
        image=dict(type='str', required=True),
        cdrom=dict(type='bool', default=True),
        rw=dict(type='bool', default=False),
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
    image = module.params.get('image')
    cdrom = module.params.get('cdrom')
    rw = module.params.get('rw')
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Get current MSD state
        msd_state = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        current_state = msd_state.get('result', {})
        
        # Get current drive settings
        drive = current_state.get('drive', {})
        current_image = drive.get('image')
        current_cdrom = drive.get('cdrom', True)
        current_rw = drive.get('rw', False)
        
        # Store the before state for diff
        before = {
            'image': current_image,
            'cdrom': current_cdrom,
            'rw': current_rw
        }
        
        # Store the after state for diff
        after = {
            'image': image,
            'cdrom': cdrom,
            'rw': rw if not cdrom else False  # rw is ignored for CD-ROM
        }
        
        # Check if image exists
        available_images = current_state.get('images', {})
        if image not in available_images and image is not None:
            module.fail_json(msg=f"Image '{image}' does not exist on the PiKVM. Available images: {', '.join(available_images.keys())}")
        
        # Determine if we need to change settings
        needs_change = has_diff(before, after)
        
        # Make the change if needed and not in check mode
        if needs_change and not module.check_mode:
            execute_pikvm_module(
                module, client, result,
                client.set_msd_params,
                image_name=image,
                cdrom=cdrom,
                rw=rw if not cdrom else None
            )
            
            # Get updated state
            updated_msd_state = execute_pikvm_module(
                module, client, result,
                client.get_msd_state
            )
            
            updated_state = updated_msd_state.get('result', {})
            result['msd_state'] = updated_state
        else:
            result['msd_state'] = current_state
        
        # Add diff to result
        if needs_change:
            result['diff'] = get_diff(before, after)
            result['changed'] = True
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to configure MSD parameters: {str(e)}")


if __name__ == '__main__':
    main()
