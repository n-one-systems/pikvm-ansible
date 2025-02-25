#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.six.moves.urllib.parse import urljoin

try:
    from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_api import PiKVMAPI, PiKVMAPIError
    HAS_PIKVM_API = True
except ImportError:
    HAS_PIKVM_API = False

# Import required libraries
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False


# Standard argument specification for all PiKVM modules
def pikvm_argument_spec():
    """
    Return standard argument spec for PiKVM modules
    """
    return dict(
        hostname=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        secret=dict(type='str', required=False, no_log=True),
        use_https=dict(type='bool', default=True),
        validate_certs=dict(type='bool', default=False)
    )


def pikvm_required_if():
    """
    Return standard required_if for PiKVM modules
    """
    return []


def pikvm_required_one_of():
    """
    Return standard required_one_of for PiKVM modules
    """
    return []


def pikvm_mutually_exclusive():
    """
    Return standard mutually_exclusive for PiKVM modules
    """
    return []


def validate_dependencies(module):
    """
    Validate required dependencies are available
    
    Args:
        module (AnsibleModule): The AnsibleModule object

    Returns:
        None
    """
    missing_deps = []
    
    if not HAS_REQUESTS:
        missing_deps.append('requests')
    
    if module.params.get('secret') and not HAS_PYOTP:
        missing_deps.append('pyotp')
    
    if missing_deps:
        module.fail_json(
            msg=f"The following Python modules are required: {', '.join(missing_deps)}",
            missing_deps=missing_deps
        )
    
    if not HAS_PIKVM_API:
        module.fail_json(
            msg="Failed to import the required PiKVM API module"
        )


def get_pikvm_client(module):
    """
    Create and return a PiKVM API client instance
    
    Args:
        module (AnsibleModule): The AnsibleModule object

    Returns:
        PiKVMAPI: The initialized PiKVM API client
    """
    # Validate dependencies
    validate_dependencies(module)
    
    # Extract params
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    secret = module.params.get('secret')
    use_https = module.params['use_https']
    validate_certs = module.params['validate_certs']
    
    try:
        client = PiKVMAPI(
            hostname=hostname,
            username=username,
            password=password,
            secret=secret,
            use_https=use_https,
            validate_certs=validate_certs
        )
        
        # Verify authentication
        if not client.check_auth():
            if not client.login():
                module.fail_json(msg="Failed to authenticate with PiKVM")
                
        return client
    
    except PiKVMAPIError as e:
        module.fail_json(msg=f"PiKVM API error: {to_native(e)}")
    except Exception as e:
        module.fail_json(msg=f"Error connecting to PiKVM: {to_native(e)}")


def update_result(result, changed=True, failed=False, msg=None, **kwargs):
    """
    Update and standardize the result dictionary
    
    Args:
        result (dict): The result dictionary to update
        changed (bool): Whether any changes were made
        failed (bool): Whether the module execution failed
        msg (str): Message to include in result
        **kwargs: Additional key/value pairs to add to result

    Returns:
        dict: The updated result dictionary
    """
    result['changed'] = changed
    result['failed'] = failed
    
    if msg:
        result['msg'] = msg
        
    # Add any additional items
    for k, v in kwargs.items():
        result[k] = v
        
    return result


def exit_with_error(module, result, msg, **kwargs):
    """
    Exit with an error message
    
    Args:
        module (AnsibleModule): The AnsibleModule object
        result (dict): The result dictionary
        msg (str): Error message
        **kwargs: Additional key/value pairs to add to result

    Returns:
        None
    """
    result = update_result(result, changed=False, failed=True, msg=msg, **kwargs)
    module.fail_json(**result)


def execute_pikvm_module(module, client, result, function, **kwargs):
    """
    Execute a PiKVM API function and handle errors
    
    Args:
        module (AnsibleModule): The AnsibleModule object
        client (PiKVMAPI): The PiKVM API client
        result (dict): The result dictionary
        function (callable): The API function to execute
        **kwargs: Arguments to pass to the function

    Returns:
        Any: The result of the API function call
    """
    try:
        return function(**kwargs)
    except PiKVMAPIError as e:
        exit_with_error(module, result, f"PiKVM API error: {to_native(e)}")
    except Exception as e:
        exit_with_error(module, result, f"Error executing PiKVM operation: {to_native(e)}")


def create_module(argument_spec=None, **kwargs):
    """
    Create an AnsibleModule instance with PiKVM standard arguments
    
    Args:
        argument_spec (dict, optional): Additional argument spec to merge with standard
        **kwargs: Additional arguments to pass to AnsibleModule constructor

    Returns:
        AnsibleModule: The initialized module
    """
    base_spec = pikvm_argument_spec()
    
    if argument_spec:
        base_spec.update(argument_spec)
        
    kwargs.setdefault('supports_check_mode', True)
    
    # Apply standard required_if/required_one_of/mutually_exclusive if not overridden
    kwargs.setdefault('required_if', pikvm_required_if())
    kwargs.setdefault('required_one_of', pikvm_required_one_of())
    kwargs.setdefault('mutually_exclusive', pikvm_mutually_exclusive())
    
    return AnsibleModule(
        argument_spec=base_spec,
        **kwargs
    )


def get_diff(before, after):
    """
    Get a unified diff of before and after states
    
    Args:
        before (dict): State before changes
        after (dict): State after changes

    Returns:
        dict: Diff information
    """
    return {
        'before': before,
        'after': after
    }


def has_diff(before, after):
    """
    Check if there's a difference between before and after states
    
    Args:
        before (dict): State before changes
        after (dict): State after changes

    Returns:
        bool: True if there's a difference, False otherwise
    """
    import json
    
    if isinstance(before, dict) and isinstance(after, dict):
        return json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)
        
    return before != after
