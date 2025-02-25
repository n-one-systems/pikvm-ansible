#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time
import threading
from functools import wraps

try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False

try:
    from ansible_collections.nsys.pikvm.plugins.module_utils.pikvm_api import PiKVMAPI, PiKVMAPIError
    HAS_PIKVM_API = True
except ImportError:
    HAS_PIKVM_API = False


class PiKVMConnectionManager:
    """
    Manages connections to PiKVM devices with connection pooling and token caching.
    """
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Implement singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PiKVMConnectionManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the connection manager"""
        if self._initialized:
            return
            
        self._connections = {}
        self._tokens = {}
        self._last_used = {}
        self._token_expiry = {}
        self._initialized = True
    
    def _get_connection_key(self, hostname, username, use_https):
        """Generate a unique key for a connection"""
        return f"{username}@{hostname}:{use_https}"
    
    def get_connection(self, hostname, username, password, secret=None, use_https=True, validate_certs=False, force_new=False):
        """
        Get a connection to a PiKVM device.
        
        Args:
            hostname (str): The hostname or IP address of the PiKVM device.
            username (str): The username for authentication.
            password (str): The password for authentication.
            secret (str, optional): The TOTP secret for two-factor authentication.
            use_https (bool, optional): Whether to use HTTPS for API requests.
            validate_certs (bool, optional): Whether to validate SSL certificates.
            force_new (bool, optional): Force creation of a new connection.
            
        Returns:
            PiKVMAPI: A connection to the PiKVM device.
        """
        if not HAS_PIKVM_API:
            raise ImportError("Failed to import PiKVMAPI")
            
        conn_key = self._get_connection_key(hostname, username, use_https)
        
        # Return existing connection if available and not forcing new
        if not force_new and conn_key in self._connections:
            conn = self._connections[conn_key]
            
            # Check if auth is still valid or can be refreshed
            try:
                if conn.check_auth():
                    # Update last used timestamp
                    self._last_used[conn_key] = time.time()
                    return conn
                    
                # Try to re-authenticate if token is invalid
                if conn.login():
                    self._last_used[conn_key] = time.time()
                    return conn
            except Exception:
                # In case of error, create a new connection
                pass
        
        # Create new connection
        conn = PiKVMAPI(
            hostname=hostname,
            username=username,
            password=password,
            secret=secret,
            use_https=use_https,
            validate_certs=validate_certs
        )
        
        # Try to login if necessary
        if not conn.check_auth():
            conn.login()
            
        # Store connection
        self._connections[conn_key] = conn
        self._last_used[conn_key] = time.time()
        
        return conn
    
    def close_connection(self, hostname, username, use_https=True):
        """
        Close a connection to a PiKVM device.
        
        Args:
            hostname (str): The hostname or IP address of the PiKVM device.
            username (str): The username for authentication.
            use_https (bool, optional): Whether the connection uses HTTPS.
            
        Returns:
            bool: True if connection was closed, False otherwise.
        """
        conn_key = self._get_connection_key(hostname, username, use_https)
        
        if conn_key in self._connections:
            conn = self._connections[conn_key]
            
            # Try to logout
            try:
                conn.logout()
            except Exception:
                pass
                
            # Remove from pools
            del self._connections[conn_key]
            self._last_used.pop(conn_key, None)
            self._tokens.pop(conn_key, None)
            self._token_expiry.pop(conn_key, None)
            
            return True
            
        return False
    
    def close_all_connections(self):
        """
        Close all connections.
        
        Returns:
            int: Number of connections closed.
        """
        count = 0
        
        # Make a copy of keys since we'll be modifying the dict
        conn_keys = list(self._connections.keys())
        
        for conn_key in conn_keys:
            conn = self._connections[conn_key]
            
            # Try to logout
            try:
                conn.logout()
            except Exception:
                pass
                
            # Remove from pools
            del self._connections[conn_key]
            self._last_used.pop(conn_key, None)
            self._tokens.pop(conn_key, None)
            self._token_expiry.pop(conn_key, None)
            
            count += 1
            
        return count
    
    def clean_unused_connections(self, max_idle_time=300):
        """
        Close connections that haven't been used for a specified time.
        
        Args:
            max_idle_time (int, optional): Maximum idle time in seconds.
            
        Returns:
            int: Number of connections closed.
        """
        count = 0
        current_time = time.time()
        
        # Make a copy of keys since we'll be modifying the dict
        conn_keys = list(self._connections.keys())
        
        for conn_key in conn_keys:
            last_used = self._last_used.get(conn_key, 0)
            
            if current_time - last_used > max_idle_time:
                # Close idle connection
                conn = self._connections[conn_key]
                
                try:
                    conn.logout()
                except Exception:
                    pass
                    
                # Remove from pools
                del self._connections[conn_key]
                self._last_used.pop(conn_key, None)
                self._tokens.pop(conn_key, None)
                self._token_expiry.pop(conn_key, None)
                
                count += 1
                
        return count
        
    def get_total_connections(self):
        """
        Get the total number of active connections.
        
        Returns:
            int: Number of active connections.
        """
        return len(self._connections)


class PiKVMTOTPManager:
    """
    Manages TOTP token generation for PiKVM 2FA authentication.
    """
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Implement singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PiKVMTOTPManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the TOTP manager"""
        if self._initialized:
            return
            
        self._totp_objects = {}
        self._totp_codes = {}
        self._code_expiry = {}
        self._initialized = True
    
    def get_totp_code(self, secret, refresh=False):
        """
        Get a TOTP code for 2FA authentication.
        
        Args:
            secret (str): The TOTP secret.
            refresh (bool, optional): Force refresh of the code.
            
        Returns:
            str: The TOTP code.
            
        Raises:
            ImportError: If pyotp is not installed.
        """
        if not HAS_PYOTP:
            raise ImportError("pyotp is required for 2FA authentication")
            
        # Return cached code if valid and not forcing refresh
        if not refresh and secret in self._totp_codes:
            if self._is_code_valid(secret):
                return self._totp_codes[secret]
        
        # Get or create TOTP object
        if secret not in self._totp_objects:
            self._totp_objects[secret] = pyotp.TOTP(secret)
            
        totp = self._totp_objects[secret]
        
        # Generate new code
        code = totp.now()
        
        # Calculate expiry
        now = int(time.time())
        expiry = now + totp.interval - (now % totp.interval)
        
        # Cache code and expiry
        self._totp_codes[secret] = code
        self._code_expiry[secret] = expiry
        
        return code
    
    def _is_code_valid(self, secret):
        """
        Check if a cached TOTP code is still valid.
        
        Args:
            secret (str): The TOTP secret.
            
        Returns:
            bool: True if the code is valid, False otherwise.
        """
        if secret not in self._code_expiry:
            return False
            
        expiry = self._code_expiry[secret]
        now = int(time.time())
        
        # Add a 5-second buffer to avoid using codes that are about to expire
        return now < (expiry - 5)
    
    def time_remaining(self, secret):
        """
        Get the time remaining for a TOTP code.
        
        Args:
            secret (str): The TOTP secret.
            
        Returns:
            int: Time remaining in seconds, or 0 if the code has expired.
        """
        if secret not in self._code_expiry:
            return 0
            
        expiry = self._code_expiry[secret]
        now = int(time.time())
        
        remaining = expiry - now
        return max(0, remaining)


# Decorator for retrying 2FA requests
def retry_with_new_totp(max_retries=1):
    """
    Decorator to retry API calls with a new TOTP code if authentication fails.
    
    Args:
        max_retries (int, optional): Maximum number of retry attempts.
        
    Returns:
        callable: The decorated function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except PiKVMAPIError as e:
                    if "TOTP might have expired" in str(e) and retries < max_retries:
                        # Force refresh of auth headers with new TOTP code
                        if args and hasattr(args[0], 'headers'):
                            args[0].headers = args[0]._get_auth_headers()
                        retries += 1
                    else:
                        raise
        return wrapper
    return decorator


# Singleton instances
connection_manager = PiKVMConnectionManager()
totp_manager = PiKVMTOTPManager()
