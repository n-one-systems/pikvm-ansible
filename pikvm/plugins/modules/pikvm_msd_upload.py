#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pikvm_msd_upload
short_description: Upload images to PiKVM Mass Storage Device (MSD)
description:
  - This module uploads image files (ISO, IMG, etc.) to a PiKVM device's Mass Storage Device (MSD).
  - It can upload from a local file or a remote URL.
  - After upload, the image is available for connection to the target server.
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
  src:
    description:
      - Path to the local image file to upload.
      - Either C(src) or C(remote_src) must be specified.
    type: path
    required: false
  remote_src:
    description:
      - URL to a remote image to upload.
      - The PiKVM will download the image directly from this URL.
      - Either C(src) or C(remote_src) must be specified.
    type: str
    required: false
  image_name:
    description:
      - Name to give the image on the PiKVM.
      - If not specified, the filename from the source will be used.
    type: str
    required: false
  timeout:
    description:
      - Timeout for remote image download in seconds.
      - Only applies when using C(remote_src).
    type: int
    default: 300
  force:
    description:
      - Whether to force upload if an image with the same name already exists.
      - If true, existing image will be removed first.
    type: bool
    default: false
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module does not support check mode.
  - For large files, this module may take a significant amount of time to complete.
'''

EXAMPLES = r'''
- name: Upload ISO from local file
  nsys.pikvm.pikvm_msd_upload:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    src: "/path/to/ubuntu.iso"

- name: Upload ISO with custom name
  nsys.pikvm.pikvm_msd_upload:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    src: "/path/to/ubuntu.iso"
    image_name: "custom-name.iso"
    force: true

- name: Upload ISO from remote URL
  nsys.pikvm.pikvm_msd_upload:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    remote_src: "https://example.com/images/ubuntu.iso"
    timeout: 600
'''

RETURN = r'''
image_name:
  description: The name of the uploaded image on the PiKVM.
  returned: success
  type: str
  sample: "ubuntu.iso"
image_size:
  description: The size of the uploaded image in bytes.
  returned: success when uploading local file
  type: int
  sample: 1073741824
remote_url:
  description: The remote URL from which the image was downloaded.
  returned: success when uploading from remote URL
  type: str
  sample: "https://example.com/images/ubuntu.iso"
'''

import os
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
        src=dict(type='path', required=False),
        remote_src=dict(type='str', required=False),
        image_name=dict(type='str', required=False),
        timeout=dict(type='int', default=300),
        force=dict(type='bool', default=False),
    )
    
    # Create the module
    module = create_module(
        argument_spec=argument_spec,
        mutually_exclusive=[['src', 'remote_src']],
        required_one_of=[['src', 'remote_src']],
        supports_check_mode=False,
    )
    
    # Initialize result
    result = dict(
        changed=False,
    )
    
    # Get parameters
    src = module.params.get('src')
    remote_src = module.params.get('remote_src')
    image_name = module.params.get('image_name')
    timeout = module.params.get('timeout')
    force = module.params.get('force')
    
    # Determine image name if not specified
    if src and not image_name:
        image_name = os.path.basename(src)
    elif remote_src and not image_name:
        # Extract filename from URL
        image_name = os.path.basename(remote_src)
    
    # Get PiKVM client
    client = get_pikvm_client(module)
    
    try:
        # Get MSD state
        msd_state = execute_pikvm_module(
            module, client, result,
            client.get_msd_state
        )
        
        if not msd_state or 'result' not in msd_state:
            module.fail_json(msg="Failed to get MSD state from PiKVM")
            
        msd_info = msd_state.get('result', {})
        storage_info = msd_info.get('storage', {})
        existing_images = storage_info.get('images', {})
        free_space = storage_info.get('free', 0)
        
        # Check if image already exists
        image_exists = image_name in existing_images
        
        # Remove existing image if force is true
        if image_exists and force:
            execute_pikvm_module(
                module, client, result,
                client.remove_msd_image,
                image_name=image_name
            )
            result['changed'] = True
        elif image_exists and not force:
            result['msg'] = f"Image '{image_name}' already exists. Use force=true to replace it."
            result['image_name'] = image_name
            module.exit_json(**result)
        
        # Upload the image
        if src:
            # Check that the file exists
            if not os.path.isfile(src):
                module.fail_json(msg=f"Source file '{src}' does not exist or is not a regular file")
            
            # Get file size for result
            file_size = os.path.getsize(src)
            result['image_size'] = file_size
            
            # Check if there's enough free space
            if free_space < file_size:
                free_space_mb = round(free_space / 1024 / 1024, 2)
                file_size_mb = round(file_size / 1024 / 1024, 2)
                module.fail_json(
                    msg=f"Not enough space on PiKVM storage. Required: {file_size_mb} MB, Available: {free_space_mb} MB",
                    required_space=file_size,
                    available_space=free_space
                )
            
            # Upload the file
            execute_pikvm_module(
                module, client, result,
                client.upload_msd_image,
                image_path=src,
                image_name=image_name
            )
            
        elif remote_src:
            # Store remote URL in result
            result['remote_url'] = remote_src
            
            # Upload from remote URL
            execute_pikvm_module(
                module, client, result,
                client.upload_msd_remote,
                url=remote_src,
                image_name=image_name,
                timeout=timeout
            )
        
        # Update result
        result['changed'] = True
        result['image_name'] = image_name
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to upload image to PiKVM: {str(e)}")


if __name__ == '__main__':
    main()
