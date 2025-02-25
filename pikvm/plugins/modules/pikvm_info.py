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
  - Can retrieve information from different API endpoints based on the requested fields.
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
      - If not specified, all categories will be returned from the /api/info endpoint.
      - Additional endpoints (atx, msd, gpio, streamer) will be queried for those specific fields.
    type: list
    elements: str
    required: false
    choices:
      - system
      - hw
      - atx
      - msd
      - gpio
      - streamer
      - all
requirements:
  - python >= 3.6
  - requests
  - pyotp (if using two-factor authentication)
notes:
  - This module supports check mode.
'''

EXAMPLES = r'''
- name: Get all system information from main info endpoint
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

- name: Get MSD information (from dedicated endpoint)
  nsys.pikvm.pikvm_info:
    hostname: "pikvm.example.com"
    username: "admin"
    password: "password"
    fields:
      - msd
  register: pikvm_msd_info

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
      returned: when requested
      sample: {"version": {"platform": "v2-hdmi-rpi4", "os": "Linux ARM 5.15.0-1030-raspi (Ubuntu 22.04)", "cdrom": "0.96"}}
    hw:
      description: Hardware information.
      type: dict
      returned: when requested
      sample: {"health": {"throttling": {"raw_bits": 0, "undervoltage": {"now": false, "past": false}}}}
    atx:
      description: ATX power management information.
      type: dict
      returned: when requested
      sample: {"enabled": true, "busy": false, "leds": {"power": true, "hdd": false}}
    msd:
      description: Mass Storage Device information.
      type: dict
      returned: when requested
      sample: {"enabled": true, "connected": false, "image": null, "drive": {"image": null, "cdrom": true, "rw": false}}
    gpio:
      description: GPIO state information.
      type: dict
      returned: when requested
    streamer:
      description: Video streamer information.
      type: dict
      returned: when requested
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_common import (
    create_module,
    get_pikvm_client,
    execute_pikvm_module,
    exit_with_error,
    update_result,
)


def get_info_from_endpoint(module, client, result, endpoint_name, endpoint_func=None):
    """
    Get information from a specific PiKVM API endpoint.
    
    Args:
        module: The Ansible module
        client: The PiKVM API client
        result: The result dictionary
        endpoint_name: The name of the endpoint (for error messages)
        endpoint_func: The client function to call for the endpoint
    
    Returns:
        dict: The endpoint information
    """
    try:
        # If no specific function is provided, use the get method with the endpoint path
        if endpoint_func is None:
            endpoint_path = f"/api/{endpoint_name}"
            response = execute_pikvm_module(
                module, client, result,
                client.get,
                path=endpoint_path
            )
        else:
            # Call the specified function
            response = execute_pikvm_module(
                module, client, result,
                endpoint_func
            )
        
        # Process response
        if response and isinstance(response, dict):
            if 'result' in response:
                return response['result']
            return response
        return {}
        
    except Exception as e:
        module.warn(f"Failed to retrieve information from {endpoint_name} endpoint: {str(e)}")
        return {}


def main():
    # Define additional arguments for this module
    argument_spec = dict(
        fields=dict(
            type='list', 
            elements='str', 
            required=False,
            choices=['system', 'hw', 'atx', 'msd', 'gpio', 'streamer', 'all']
        )
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
        # Map fields to API endpoints and client functions
        endpoints = {
            'info': {
                'fields': None if not fields else [f for f in fields if f in ['system', 'hw'] or f == 'all'],
                'function': client.get_system_info
            },
            'atx': {
                'fields': ['atx'],
                'function': client.get_atx_state
            },
            'msd': {
                'fields': ['msd'],
                'function': client.get_msd_state
            },
            'gpio': {
                'fields': ['gpio'],
                'function': client.get_gpio_state
            },
            'streamer': {
                'fields': ['streamer'],
                'function': client.get_streamer_state
            }
        }
        
        # Determine which endpoints to query
        query_endpoints = []
        
        if fields:
            # If 'all' is specified, query all endpoints
            if 'all' in fields:
                query_endpoints = list(endpoints.keys())
            else:
                # Otherwise, determine endpoints based on requested fields
                for endpoint, config in endpoints.items():
                    if endpoint == 'info':
                        if any(f in ['system', 'hw'] for f in fields):
                            query_endpoints.append(endpoint)
                    elif any(f in config['fields'] for f in fields):
                        query_endpoints.append(endpoint)
        else:
            # Default to querying just the main info endpoint
            query_endpoints = ['info']
        
        # Query each endpoint and merge results
        for endpoint in query_endpoints:
            config = endpoints[endpoint]
            
            # Skip info endpoint if no relevant fields are requested
            if endpoint == 'info' and config['fields'] == []:
                continue
                
            # Get endpoint information
            if endpoint == 'info':
                # For info endpoint, pass fields parameter
                info_data = execute_pikvm_module(
                    module, client, result,
                    config['function'],
                    fields=config['fields']
                )
                
                if info_data and 'result' in info_data:
                    for key, value in info_data['result'].items():
                        result['info'][key] = value
            else:
                # For other endpoints, call the specific function
                endpoint_data = get_info_from_endpoint(
                    module, client, result,
                    endpoint,
                    config['function']
                )
                
                # Add endpoint data to result
                if endpoint_data:
                    # Use the endpoint name as the key
                    field_name = config['fields'][0]  # First field name in the list
                    result['info'][field_name] = endpoint_data
        
        # Exit successfully
        module.exit_json(**result)
        
    except Exception as e:
        exit_with_error(module, result, f"Failed to retrieve PiKVM information: {str(e)}")


if __name__ == '__main__':
    main()
