#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_msd
short_description: Manage PiKVM Mass Storage Device (MSD)
description:
  - This module manages the Mass Storage Device functionality of PiKVM.
  - It allows uploading images, downloading remote images, configuring media types,
    connecting/disconnecting the device, setting read modes, and removing images.
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
      - The desired state of the MSD or image.
      - When 'present', ensures the specified image is available or uploads it.
      - When 'connected', ensures the MSD is connected with the specified image.
      - When 'disconnected', ensures the MSD is disconnected.
      - When 'absent', ensures the specified image is removed.
      - When 'reset', resets the MSD device.
    type: str
    choices: ['present', 'connected', 'disconnected', 'absent', 'reset']
    default: 'connected'
  image_name:
    description:
      - The name of the image file to manage.
      - For local uploads, this will be the name assigned on the PiKVM.
      - For state 'connected', this is the image to connect.
      - Required for states 'present', 'connected', and 'absent'.
      - If not provided with 'present' and src is provided, the basename will be used.
    type: str
    required: false
  src:
    description:
      - The local path to the image file to upload.
      - Only used when state is 'present'.
    type: path
    required: false
  remote_src:
    description:
      - The URL of a remote image file to download to the PiKVM.
      - Only used when state is 'present'.
    type: str
    required: false
  remote_timeout:
    description:
      - Timeout in seconds for remote image downloads.
      - Only used when remote_src is specified.
    type: int
    default: 30
  media_type:
    description:
      - The type of media to emulate.
      - When set to 'cdrom', the MSD will be read-only.
    type: str
    choices: ['cdrom', 'flash']
    default: 'cdrom'
  read_only:
    description:
      - Whether the MSD should be read-only.
      - Ignored when media_type is 'cdrom' (always read-only).
      - Only applicable when media_type is 'flash'.
    type: bool
    default: true
  wait:
    description:
      - Whether to wait for operations to complete.
    type: bool
    default: true
requirements:
  - python >= 3.6
  - pyotp (if using two-factor authentication)
notes:
  - Check mode is supported.
'''

EXAMPLES = r'''
- name: Upload an ISO image to PiKVM
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: present
    src: "/path/to/image.iso"
    image_name: "ubuntu.iso"
    media_type: cdrom

- name: Download a remote ISO to PiKVM
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: present
    remote_src: "http://example.com/images/ubuntu.iso"
    image_name: "ubuntu.iso"
    remote_timeout: 60

- name: Connect an image to the MSD
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: connected
    image_name: "ubuntu.iso"
    media_type: cdrom

- name: Connect a flash image with read-write mode
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: connected
    image_name: "data.img"
    media_type: flash
    read_only: false

- name: Disconnect the MSD
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: disconnected

- name: Remove an image from the PiKVM
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: absent
    image_name: "ubuntu.iso"

- name: Reset the MSD
  nsys.pikvm.pikvm_msd:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    state: reset
'''

RETURN = r'''
msd_state:
  description: The current state of the MSD.
  returned: success
  type: dict
  sample: {
    "enabled": true,
    "connected": true,
    "features": {
        "cdrom": true,
        "rw": true
    },
    "drive": {
        "image": "ubuntu.iso",
        "cdrom": true,
        "rw": false
    },
    "images": {
        "ubuntu.iso": {
            "in_use": true,
            "mime": "application/octet-stream",
            "size": 983040
        }
    }
  }
message:
  description: Informational message about the action performed.
  returned: always
  type: str
  sample: "Image ubuntu.iso uploaded and connected"
'''

import os
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    create_module,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
    update_result,
    has_diff
)


def upload_image(module, client, result, src, image_name, check_mode=False):
    """
    Upload an image from local file to PiKVM.
    """
    # Validate file exists
    if not os.path.isfile(src):
        exit_with_error(module, result, f"Source file {src} does not exist or is not a file")
        
    # Use filename if image_name not provided
    if not image_name:
        image_name = os.path.basename(src)
    
    # Get current MSD state for comparison
    msd_state_before = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Check if image already exists
    image_exists = False
    if 'result' in msd_state_before and 'images' in msd_state_before['result']:
        image_exists = image_name in msd_state_before['result']['images']
        
    # Skip if the image already exists (to avoid re-uploading)
    if image_exists:
        result['message'] = f"Image {image_name} already exists"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=False)
    
    # Skip actual upload in check mode
    if check_mode:
        result['message'] = f"Would upload image {src} as {image_name}"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=True)
    
    # Perform the upload
    try:
        execute_pikvm_module(
            module, client, result,
            client.upload_msd_image,
            image_path=src,
            image_name=image_name
        )
        
        # Get updated MSD state
        msd_state_after = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        result['message'] = f"Image {image_name} uploaded successfully"
        result['msd_state'] = msd_state_after.get('result', {})
        return update_result(result, changed=True)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to upload image: {to_native(e)}")


def download_remote_image(module, client, result, remote_src, image_name, timeout, check_mode=False):
    """
    Download an image from a remote URL to PiKVM.
    """
    # Use filename from URL if image_name not provided
    if not image_name:
        image_name = os.path.basename(remote_src)
    
    # Get current MSD state for comparison
    msd_state_before = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Check if image already exists
    image_exists = False
    if 'result' in msd_state_before and 'images' in msd_state_before['result']:
        image_exists = image_name in msd_state_before['result']['images']
        
    # Skip if the image already exists (to avoid re-downloading)
    if image_exists:
        result['message'] = f"Image {image_name} already exists"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=False)
    
    # Skip actual download in check mode
    if check_mode:
        result['message'] = f"Would download image from {remote_src} as {image_name}"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=True)
    
    # Perform the download
    try:
        execute_pikvm_module(
            module, client, result,
            client.upload_msd_remote,
            url=remote_src,
            image_name=image_name,
            timeout=timeout
        )
        
        # Get updated MSD state
        msd_state_after = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        result['message'] = f"Image {image_name} downloaded successfully from {remote_src}"
        result['msd_state'] = msd_state_after.get('result', {})
        return update_result(result, changed=True)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to download image from {remote_src}: {to_native(e)}")


def configure_and_connect_msd(module, client, result, image_name, media_type, read_only, check_mode=False):
    """
    Configure MSD parameters and connect it.
    """
    # Get current MSD state
    msd_state_before = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Extract current configuration
    cur_state = msd_state_before.get('result', {})
    cur_drive = cur_state.get('drive', {})
    cur_image = cur_drive.get('image')
    cur_cdrom = cur_drive.get('cdrom', True)
    cur_rw = cur_drive.get('rw', False)
    cur_connected = cur_state.get('connected', False)
    
    # Determine if image exists
    image_exists = False
    if 'images' in cur_state:
        image_exists = image_name in cur_state['images']
        
    if not image_exists:
        exit_with_error(module, result, f"Image {image_name} does not exist on the PiKVM")
    
    # Determine if changes are needed
    is_cdrom = media_type == 'cdrom'
    need_config_change = (
        cur_image != image_name or
        cur_cdrom != is_cdrom or
        (not is_cdrom and cur_rw != (not read_only))
    )
    need_connect = not cur_connected
    
    # If no changes needed
    if not need_config_change and not need_connect:
        result['message'] = f"MSD already configured and connected with image {image_name}"
        result['msd_state'] = cur_state
        return update_result(result, changed=False)
    
    # Skip actual changes in check mode
    if check_mode:
        message_parts = []
        if need_config_change:
            message_parts.append(f"Would configure MSD with image {image_name}")
        if need_connect:
            message_parts.append("Would connect MSD")
            
        result['message'] = " and ".join(message_parts)
        result['msd_state'] = cur_state
        return update_result(result, changed=True)
    
    # Apply configuration if needed
    if need_config_change:
        execute_pikvm_module(
            module, client, result,
            client.set_msd_params,
            image_name=image_name,
            cdrom=is_cdrom,
            rw=not read_only if not is_cdrom else None
        )
    
    # Connect MSD if needed
    if need_connect:
        execute_pikvm_module(
            module, client, result,
            client.connect_msd,
            connected=True
        )
    
    # Get updated MSD state
    msd_state_after = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Prepare result message
    message_parts = []
    if need_config_change:
        message_parts.append(f"MSD configured with image {image_name}")
    if need_connect:
        message_parts.append("MSD connected")
        
    result['message'] = " and ".join(message_parts)
    result['msd_state'] = msd_state_after.get('result', {})
    return update_result(result, changed=True)


def disconnect_msd(module, client, result, check_mode=False):
    """
    Disconnect the MSD.
    """
    # Get current MSD state
    msd_state_before = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Check if already disconnected
    cur_connected = msd_state_before.get('result', {}).get('connected', False)
    
    if not cur_connected:
        result['message'] = "MSD already disconnected"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=False)
    
    # Skip actual disconnect in check mode
    if check_mode:
        result['message'] = "Would disconnect MSD"
        result['msd_state'] = msd_state_before.get('result', {})
        return update_result(result, changed=True)
    
    # Disconnect the MSD
    execute_pikvm_module(
        module, client, result,
        client.connect_msd,
        connected=False
    )
    
    # Get updated MSD state
    msd_state_after = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    result['message'] = "MSD disconnected"
    result['msd_state'] = msd_state_after.get('result', {})
    return update_result(result, changed=True)


def remove_image(module, client, result, image_name, check_mode=False):
    """
    Remove an image from the PiKVM.
    """
    # Get current MSD state
    msd_state_before = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    # Check if image exists
    cur_state = msd_state_before.get('result', {})
    image_exists = False
    if 'images' in cur_state:
        image_exists = image_name in cur_state['images']
        
    if not image_exists:
        result['message'] = f"Image {image_name} does not exist"
        result['msd_state'] = cur_state
        return update_result(result, changed=False)
    
    # Check if image is in use
    image_in_use = False
    if 'images' in cur_state and image_name in cur_state['images']:
        image_in_use = cur_state['images'][image_name].get('in_use', False)
        
    # Check if MSD is connected with this image
    cur_connected = cur_state.get('connected', False)
    cur_image = cur_state.get('drive', {}).get('image')
    
    # Skip actual removal in check mode
    if check_mode:
        message = f"Would remove image {image_name}"
        if image_in_use or (cur_connected and cur_image == image_name):
            message += " (requires disconnecting MSD first)"
            
        result['message'] = message
        result['msd_state'] = cur_state
        return update_result(result, changed=True)
    
    # Disconnect MSD if necessary
    if cur_connected and cur_image == image_name:
        execute_pikvm_module(
            module, client, result,
            client.connect_msd,
            connected=False
        )
    
    # Remove the image
    execute_pikvm_module(
        module, client, result,
        client.remove_msd_image,
        image_name=image_name
    )
    
    # Get updated MSD state
    msd_state_after = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    result['message'] = f"Image {image_name} removed"
    result['msd_state'] = msd_state_after.get('result', {})
    return update_result(result, changed=True)


def reset_msd(module, client, result, check_mode=False):
    """
    Reset the MSD.
    """
    # Skip actual reset in check mode
    if check_mode:
        result['message'] = "Would reset MSD"
        return update_result(result, changed=True)
    
    # Reset the MSD
    execute_pikvm_module(
        module, client, result,
        client.reset_msd
    )
    
    # Get updated MSD state
    msd_state_after = execute_pikvm_module(
        module, client, result,
        client.get_msd_state
    )
    
    result['message'] = "MSD reset"
    result['msd_state'] = msd_state_after.get('result', {})
    return update_result(result, changed=True)


def main():
    # Define additional arguments for this module
    argument_spec = dict(
        state=dict(
            type='str',
            choices=['present', 'connected', 'disconnected', 'absent', 'reset'],
            default='connected'
        ),
        image_name=dict(type='str', required=False),
        src=dict(type='path', required=False),
        remote_src=dict(type='str', required=False),
        remote_timeout=dict(type='int', default=30),
        media_type=dict(type='str', choices=['cdrom', 'flash'], default='cdrom'),
        read_only=dict(type='bool', default=True),
        wait=dict(type='bool', default=True)
    )
    
    # Define required parameters based on state
    required_if = [
        ('state', 'present', ['image_name', 'src', 'remote_src'], True),
        ('state', 'connected', ['image_name'], False),
        ('state', 'absent', ['image_name'], False),
    ]
    
    # Define mutually exclusive parameters
    mutually_exclusive = [
        ['src', 'remote_src']
    ]
    
    # Create the module
    module = create_module(
        argument_spec=argument_spec,
        required_if=required_if,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True
    )
    
    # Extract parameters
    state = module.params['state']
    image_name = module.params['image_name']
    src = module.params.get('src')
    remote_src = module.params.get('remote_src')
    remote_timeout = module.params['remote_timeout']
    media_type = module.params['media_type']
    read_only = module.params['read_only']
    wait = module.params['wait']
    check_mode = module.check_mode
    
    # Initialize result
    result = dict(
        changed=False,
        message='',
        msd_state={}
    )
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    # Perform actions based on state
    try:
        if state == 'present':
            # Upload local image
            if src:
                upload_image(module, client, result, src, image_name, check_mode)
            # Download remote image
            elif remote_src:
                download_remote_image(module, client, result, remote_src, image_name, remote_timeout, check_mode)
            else:
                exit_with_error(module, result, "Either src or remote_src must be provided when state is 'present'")
                
        elif state == 'connected':
            if not image_name:
                exit_with_error(module, result, "image_name is required when state is 'connected'")
                
            configure_and_connect_msd(module, client, result, image_name, media_type, read_only, check_mode)
            
        elif state == 'disconnected':
            disconnect_msd(module, client, result, check_mode)
            
        elif state == 'absent':
            if not image_name:
                exit_with_error(module, result, "image_name is required when state is 'absent'")
                
            remove_image(module, client, result, image_name, check_mode)
            
        elif state == 'reset':
            reset_msd(module, client, result, check_mode)
            
        # Exit with the result
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Error managing PiKVM MSD: {to_native(e)}")


if __name__ == '__main__':
    main()