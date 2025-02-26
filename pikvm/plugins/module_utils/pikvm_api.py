#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import time
from urllib.parse import urljoin, quote

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


class PiKVMAPIError(Exception):
    """Exception raised for PiKVM API errors."""
    pass


class PiKVMAPI:
    """
    Base class for interacting with the PiKVM API.
    """

    def __init__(self, hostname, username, password, secret=None, use_https=True, validate_certs=False):
        """
        Initialize the PiKVM API client.

        Args:
            hostname (str): The hostname or IP address of the PiKVM device.
            username (str): The username for authentication.
            password (str): The password for authentication.
            secret (str, optional): The TOTP secret for two-factor authentication.
            use_https (bool, optional): Whether to use HTTPS for API requests. Defaults to True.
            validate_certs (bool, optional): Whether to validate SSL certificates. Defaults to False.
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.secret = secret
        self.use_https = use_https
        self.validate_certs = validate_certs
        
        self.base_url = f"{'https' if use_https else 'http'}://{hostname}"
        self.session = requests.Session()
        self.session.verify = validate_certs
        
        self.auth_token = None
        self.headers = self._get_auth_headers()

    def _get_auth_headers(self):
        """
        Get headers for authentication.

        Returns:
            dict: The headers for authentication.
        """
        passwd = self.password
        
        # Add TOTP code if secret is provided
        if self.secret and HAS_PYOTP:
            totp = pyotp.TOTP(self.secret)
            passwd += totp.now()
        
        headers = {
            "X-KVMD-User": self.username,
            "X-KVMD-Passwd": passwd
        }
        
        return headers
    
    def _build_url(self, path):
        """
        Build the full URL for an API request.

        Args:
            path (str): The API endpoint path.

        Returns:
            str: The full URL.
        """
        # Ensure path starts with a slash
        if not path.startswith('/'):
            path = '/' + path
            
        return urljoin(self.base_url, path)
    
    def _handle_response(self, response, expected_status=200):
        """
        Handle an API response, raising exceptions for errors.

        Args:
            response (requests.Response): The API response.
            expected_status (int, optional): The expected HTTP status code. Defaults to 200.

        Returns:
            dict: The JSON response data if successful.

        Raises:
            PiKVMAPIError: If the API request fails.
        """
        if response.status_code == 401:
            raise PiKVMAPIError("Authentication required")
        
        if response.status_code == 403:
            # Handle potential TOTP expiration
            if self.secret and HAS_PYOTP:
                # TOTP code might have expired, refresh headers with new code
                self.headers = self._get_auth_headers()
                # The caller should retry the request
                raise PiKVMAPIError("Authentication failed - TOTP might have expired")
            else:
                raise PiKVMAPIError("Authentication failed - incorrect credentials")
        
        if response.status_code != expected_status:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
            except ValueError:
                error_msg = response.text or f"HTTP {response.status_code}"
                
            raise PiKVMAPIError(f"API request failed: {error_msg}")
        
        try:
            data = response.json()
            
            # Check for API-level errors
            if isinstance(data, dict) and data.get('ok') is False:
                error_msg = data.get('error', 'Unknown API error')
                raise PiKVMAPIError(f"API returned error: {error_msg}")
                
            return data
        except ValueError:
            if response.content:
                return response.content
            return None
    
    def login(self):
        """
        Log in to the PiKVM API and get an authentication token.

        Returns:
            bool: True if login successful, False otherwise.
        """
        url = self._build_url('/api/auth/login')
        data = {
            'user': self.username,
            'passwd': self.password
        }
        
        # Add TOTP code if secret is provided
        if self.secret and HAS_PYOTP:
            totp = pyotp.TOTP(self.secret)
            data['passwd'] += totp.now()
        
        response = self.session.post(url, data=data, verify=self.validate_certs)
        
        if response.status_code == 200:
            # Extract auth token from cookies
            self.auth_token = response.cookies.get('auth_token')
            return True
        
        return False
    
    def check_auth(self):
        """
        Check if currently authenticated.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        url = self._build_url('/api/auth/check')
        
        # Try with session token if available
        if self.auth_token:
            response = self.session.get(url, verify=self.validate_certs)
            if response.status_code == 200:
                return True
            
            # Token might be invalid, try with headers
            self.auth_token = None
        
        # Try with auth headers
        response = self.session.get(url, headers=self.headers, verify=self.validate_certs)
        return response.status_code == 200
    
    def logout(self):
        """
        Log out and invalidate the authentication token.

        Returns:
            bool: True if logout successful, False otherwise.
        """
        if not self.auth_token:
            return True  # Already logged out
            
        url = self._build_url('/api/auth/logout')
        response = self.session.post(url, verify=self.validate_certs)
        
        if response.status_code == 200:
            self.auth_token = None
            return True
            
        return False
    
    def get(self, path, params=None):
        """
        Perform a GET request to the API.

        Args:
            path (str): The API endpoint path.
            params (dict, optional): Query parameters.

        Returns:
            dict: The API response data.
        """
        url = self._build_url(path)
        
        # Try with session token if available
        if self.auth_token:
            response = self.session.get(url, params=params, verify=self.validate_certs)
        else:
            # Use auth headers
            response = self.session.get(url, headers=self.headers, params=params, verify=self.validate_certs)
        
        return self._handle_response(response)
    
    def post(self, path, data=None, params=None, files=None, expected_status=200):
        """
        Perform a POST request to the API.

        Args:
            path (str): The API endpoint path.
            data (dict, optional): The request body data.
            params (dict, optional): Query parameters.
            files (dict, optional): Files to upload.
            expected_status (int, optional): Expected HTTP status code.

        Returns:
            dict: The API response data.
        """
        url = self._build_url(path)
        
        # Try with session token if available
        if self.auth_token:
            response = self.session.post(url, data=data, params=params, files=files, verify=self.validate_certs)
        else:
            # Use auth headers
            response = self.session.post(url, headers=self.headers, data=data, params=params, files=files, verify=self.validate_certs)
        
        return self._handle_response(response, expected_status)
    
    def get_system_info(self, fields=None):
        """
        Get system information.

        Args:
            fields (list, optional): List of fields to include in the response.

        Returns:
            dict: System information.
        """
        params = None
        if fields:
            params = {'fields': ','.join(fields)}
            
        return self.get('/api/info', params=params)
    
    def get_system_log(self, follow=False, seek=None):
        """
        Get system logs.

        Args:
            follow (bool, optional): Whether to follow log in real-time.
            seek (int, optional): Time in seconds to retrieve logs for.

        Returns:
            str: System logs.
        """
        params = {}
        if follow:
            params['follow'] = 1
        if seek:
            params['seek'] = seek
            
        response = self.session.get(
            self._build_url('/api/log'),
            headers=self.headers if not self.auth_token else None,
            params=params,
            verify=self.validate_certs,
            stream=follow
        )
        
        if follow:
            return response  # Return the response object for streaming
        
        if response.status_code != 200:
            self._handle_response(response)
            
        return response.text

    def get_prometheus_metrics(self):
        """
        Get Prometheus metrics.

        Returns:
            str: Prometheus metrics.
        """
        response = self.session.get(
            self._build_url('/api/export/prometheus/metrics'),
            headers=self.headers if not self.auth_token else None,
            verify=self.validate_certs
        )
        
        if response.status_code != 200:
            self._handle_response(response)
            
        return response.text

    # ATX Power Management methods
    
    def get_atx_state(self):
        """
        Get the current ATX state.

        Returns:
            dict: ATX state information.
        """
        return self.get('/api/atx')
    
    def set_atx_power(self, action, wait=True):
        """
        Change ATX power state.

        Args:
            action (str): The desired power state. Must be 'on', 'off', 'off_hard', or 'reset_hard'.
            wait (bool, optional): Whether to wait for the operation to complete. Defaults to True.

        Returns:
            dict: Response data.
        """
        if action not in ['on', 'off', 'off_hard', 'reset_hard']:
            raise PiKVMAPIError(f"Invalid ATX power action: {action}")
            
        params = {
            'action': action
        }
        
        if wait:
            params['wait'] = 1
            
        return self.post('/api/atx/power', params=params)
    
    def click_atx_button(self, button, wait=True):
        """
        Send an ATX button press event.

        Args:
            button (str): The button to press. Must be 'power', 'power_long', or 'reset'.
            wait (bool, optional): Whether to wait for the operation to complete. Defaults to True.

        Returns:
            dict: Response data.
        """
        if button not in ['power', 'power_long', 'reset']:
            raise PiKVMAPIError(f"Invalid ATX button: {button}")
            
        params = {
            'button': button
        }
        
        if wait:
            params['wait'] = 1
            
        return self.post('/api/atx/click', params=params)
    
    # MSD (Mass Storage Device) methods
    
    def get_msd_state(self):
        """
        Get the current Mass Storage Device state.

        Returns:
            dict: MSD state information.
        """
        return self.get('/api/msd')
    
    def upload_msd_image(self, image_path, image_name=None):
        """
        Upload an image file to the MSD.

        Args:
            image_path (str): Path to the local image file.
            image_name (str, optional): Name to give the image on the server.
                                      If not provided, the filename from image_path will be used.

        Returns:
            dict: Response data.
        """
        import os
        
        if not os.path.isfile(image_path):
            raise PiKVMAPIError(f"Image file not found: {image_path}")
            
        # Use the filename if image_name is not provided
        if not image_name:
            image_name = os.path.basename(image_path)
            
        params = {
            'image': image_name
        }
        
        with open(image_path, 'rb') as f:
            return self.post('/api/msd/write', params=params, data=f.read())

    def upload_msd_remote(self, url, image_name=None, timeout=10):
        """
        Upload an image from a remote URL to the MSD.

        Args:
            url (str): Remote image URL.
            image_name (str, optional): Name to give the image on the server.
            timeout (int, optional): Remote request timeout in seconds. Defaults to 10.

        Returns:
            dict: Response data.
        """
        params = {
            'url': url,
            'timeout': timeout
        }
        
        if image_name:
            params['image'] = image_name
            
        return self.post('/api/msd/write_remote', params=params)
    
    def set_msd_params(self, image_name, cdrom=True, rw=None):
        """
        Set MSD parameters.

        Args:
            image_name (str): Image name.
            cdrom (bool, optional): Whether to use CD-ROM mode. Defaults to True.
            rw (bool, optional): Whether to make the drive read-write. 
                               Ignored when cdrom=True. Defaults to None.

        Returns:
            dict: Response data.
        """
        params = {
            'image': image_name,
            'cdrom': 1 if cdrom else 0
        }
        
        if rw is not None and not cdrom:
            params['rw'] = 1 if rw else 0
            
        return self.post('/api/msd/set_params', params=params)
    
    def connect_msd(self, connected=True):
        """
        Connect or disconnect the MSD.

        Args:
            connected (bool, optional): Whether to connect or disconnect. Defaults to True.

        Returns:
            dict: Response data.
        """
        params = {
            'connected': 1 if connected else 0
        }
            
        return self.post('/api/msd/set_connected', params=params)
    
    def remove_msd_image(self, image_name):
        """
        Remove an MSD image.

        Args:
            image_name (str): Image name to remove.

        Returns:
            dict: Response data.
        """
        params = {
            'image': image_name
        }
            
        return self.post('/api/msd/remove', params=params)
    
    def reset_msd(self):
        """
        Reset the MSD.

        Returns:
            dict: Response data.
        """
        return self.post('/api/msd/reset')
    
    # GPIO methods
    
    def get_gpio_state(self):
        """
        Get the current GPIO state.

        Returns:
            dict: GPIO state information.
        """
        return self.get('/api/gpio')
    
    def switch_gpio_channel(self, channel, state, wait=True):
        """
        Switch a GPIO channel state.

        Args:
            channel (str): The GPIO channel.
            state (int): The new state (0 or 1).
            wait (bool, optional): Whether to wait for the operation to complete. Defaults to True.

        Returns:
            dict: Response data.
        """
        params = {
            'channel': channel,
            'state': state
        }
        
        if wait:
            params['wait'] = 1
            
        return self.post('/api/gpio/switch', params=params)
    
    def pulse_gpio_channel(self, channel, delay=0, wait=True):
        """
        Pulse a GPIO channel.

        Args:
            channel (str): The GPIO channel.
            delay (float, optional): Pulse time in seconds. Defaults to 0.
            wait (bool, optional): Whether to wait for the operation to complete. Defaults to True.

        Returns:
            dict: Response data.
        """
        params = {
            'channel': channel
        }
        
        if delay:
            params['delay'] = delay
            
        if wait:
            params['wait'] = 1
            
        return self.post('/api/gpio/pulse', params=params)
    
    # Streamer methods
    
    def get_streamer_state(self):
        """
        Get the streamer state.

        Returns:
            dict: Streamer state information.
        """
        return self.get('/api/streamer')
    
    def get_streamer_snapshot(self, ocr=False):
        """
        Capture a screen snapshot.

        Args:
            ocr (bool, optional): Whether to return OCR-recognized text instead of image. Defaults to False.

        Returns:
            bytes: Image data or OCR text.
        """
        params = {
            'allow_offline': 1
        }
        
        if ocr:
            params['ocr'] = 1
            
        response = self.session.get(
            self._build_url('/api/streamer/snapshot'),
            headers=self.headers if not self.auth_token else None,
            params=params,
            verify=self.validate_certs
        )
        
        if response.status_code != 200:
            self._handle_response(response)
            
        return response.content
