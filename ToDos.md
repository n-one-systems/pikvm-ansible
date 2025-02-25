# PiKVM Ansible Collection Implementation ToDos

This document outlines the implementation plan for the nsys.pikvm Ansible collection. It provides a structured approach to developing all the features described in the README.md, with a focus on reusability, maintainability, and extensibility.

## 1. Project Structure Setup

### 1.1 Initialize Collection Framework - done
- **Description**: Create the initial collection structure using ansible-galaxy
- **Implementation**:
  ```bash
  ansible-galaxy collection init nsys.pikvm
  ```
- **Expected Outcome**: Basic directory structure for the collection

### 1.2 Setup Directory Structure - done
- **Description**: Create all necessary directories for the collection components
- **Implementation**:
  ```bash
  mkdir -p plugins/modules/
  mkdir -p plugins/module_utils/
  mkdir -p roles/
  mkdir -p playbooks/
  mkdir -p docs/
  mkdir -p tests/integration
  mkdir -p tests/unit
  ```
- **Expected Outcome**: Complete directory structure ready for development

### 1.3 Configure Basic Metadata - done
- **Description**: Create galaxy.yml and other metadata files
- **Implementation**:
  - Add proper metadata to galaxy.yml (version, author, description, etc.)
  - Create README.md with basic usage instructions
  - Add LICENSE file
- **Expected Outcome**: Collection metadata properly configured

## 2. Core Utilities Development

### 2.1 API Interaction Layer - done
- **Description**: Develop the base API interaction utilities that all modules will use
- **Implementation**: Create `plugins/module_utils/pikvm_api.py` with:
  - Base API class for HTTP interactions with PiKVM endpoints
  - Authentication methods (standard and 2FA)
  - WebSocket connection handling
  - Error handling and standardized responses
  - Path building and URL construction utilities
  - Session management
- **Dependencies**: None
- **Expected Outcome**: Reusable API utility class that can be imported by all modules

### 2.2 Common Module Utilities - done
- **Description**: Create shared utilities for all modules to reduce code duplication
- **Implementation**: Create `plugins/module_utils/pikvm_common.py` with:
  - Standard argument spec definitions (hostname, username, password)
  - Result formatting functions
  - Shared parameter validation logic
  - Common status checking functions
  - Helper methods for handling responses
- **Dependencies**: 2.1 API Interaction Layer
- **Expected Outcome**: Common utilities that standardize module behavior

### 2.3 Connection Management - done
- **Description**: Develop utilities for managing connections and authentication
- **Implementation**: Create `plugins/module_utils/pikvm_connection.py` with:
  - Connection pooling functionality
  - Session token caching
  - Re-authentication logic
  - 2FA token generation
- **Dependencies**: 2.1 API Interaction Layer
- **Expected Outcome**: Efficient connection management system for all modules

## 3. Module Implementation

### 3.1 pikvm_info Module  - done
- **Description**: Implement module to retrieve system information
- **Implementation**: Create `plugins/modules/pikvm_info.py` with:
  - Standard connection parameters
  - Optional field filtering
  - System information retrieval
  - Formatted results return
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities
- **Expected Outcome**: Functional module that retrieves and returns PiKVM system information

### 3.2 pikvm_atx Module
- **Description**: Implement module to control ATX power operations
- **Implementation**: Create `plugins/modules/pikvm_atx.py` with:
  - Power control actions (on, off, off_hard, reset_hard)
  - Button click operations (power, power_long, reset)
  - State checking for idempotence
  - Wait parameter support
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities
- **Expected Outcome**: Module that can control and report ATX power operations

### 3.3 pikvm_msd Module
- **Description**: Implement module to manage Mass Storage Device operations
- **Implementation**: Create `plugins/modules/pikvm_msd.py` with:
  - Upload image functionality (local file)
  - Remote image download capability
  - Media type configuration (cdrom/flash)
  - Connect/disconnect operations
  - Read-only/read-write mode setting
  - Image removal functionality
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities
- **Expected Outcome**: Complete MSD management module

### 3.4 pikvm_keyboard Module
- **Description**: Implement module to send keyboard input via WebSocket
- **Implementation**: Create `plugins/modules/pikvm_keyboard.py` with:
  - Text input sending
  - Special key support (<F1>, <Enter>, etc.)
  - Key combination support (Ctrl+Alt+Del)
  - Input verification
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities, 2.3 Connection Management
- **Expected Outcome**: Module that can send keyboard input reliably

### 3.5 pikvm_gpio Module
- **Description**: Implement module to control GPIO channels
- **Implementation**: Create `plugins/modules/pikvm_gpio.py` with:
  - GPIO state reading
  - Channel switching functionality
  - Pulse operation support
  - State verification for idempotence
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities
- **Expected Outcome**: Module for complete GPIO management

### 3.6 pikvm_snapshot Module
- **Description**: Implement module to capture screen snapshots
- **Implementation**: Create `plugins/modules/pikvm_snapshot.py` with:
  - Screen capture functionality
  - OCR text recognition option
  - Path and filename configuration
  - Multiple format support
- **Dependencies**: 2.1 API Layer, 2.2 Common Utilities
- **Expected Outcome**: Module that can capture and save screen snapshots

## 4. Role Development

### 4.1 pikvm_setup Role
- **Description**: Create role for basic PiKVM configuration
- **Implementation**: 
  - Create role structure in `roles/pikvm_setup/`
  - Implement tasks for basic configuration
  - Add default variables and templates
  - Create handlers for service management
  - Document all variables and options
- **Dependencies**: All applicable modules
- **Expected Outcome**: Role that configures PiKVM with standard settings

### 4.2 pikvm_boot_iso Role
- **Description**: Create role for booting a server from ISO using PiKVM
- **Implementation**:
  - Create role structure in `roles/pikvm_boot_iso/`
  - Implement tasks for ISO upload and connection
  - Add power cycling and key sending operations
  - Create boot sequence automation
  - Add verification and recovery mechanisms
- **Dependencies**: pikvm_msd, pikvm_atx, pikvm_keyboard modules
- **Expected Outcome**: Role that automates the process of booting a server from an ISO

## 5. Playbook Creation

### 5.1 Basic Power Control Playbook
- **Description**: Create example playbook for server power management
- **Implementation**: Create `playbooks/power_control.yml` with:
  - Power on/off operations
  - Reset operations
  - Status checking
  - Error handling
- **Dependencies**: pikvm_atx module
- **Expected Outcome**: Functional playbook demonstrating power control

### 5.2 OS Installation Playbook
- **Description**: Create example playbook for automated OS installation
- **Implementation**: Create `playbooks/os_installation.yml` with:
  - ISO upload and connection
  - Boot sequence automation
  - Installation parameter input
  - Progress monitoring
- **Dependencies**: Multiple modules, pikvm_boot_iso role
- **Expected Outcome**: Comprehensive playbook demonstrating OS installation automation

### 5.3 Server Maintenance Playbook
- **Description**: Create playbook for common server maintenance tasks
- **Implementation**: Create `playbooks/server_maintenance.yml` with:
  - BIOS/BMC access procedures
  - Firmware update workflows
  - Health check operations
- **Dependencies**: Multiple modules
- **Expected Outcome**: Useful playbook for server maintenance automation

## 6. Testing Framework

### 6.1 Unit Test Framework
- **Description**: Set up unit testing for modules and utilities
- **Implementation**:
  - Create test structure in `tests/unit/`
  - Implement test cases for each module
  - Add mocking for API responses
  - Create CI configuration for automated testing
- **Dependencies**: All modules and utilities
- **Expected Outcome**: Comprehensive unit test suite

### 6.2 Integration Test Framework
- **Description**: Set up integration testing with actual PiKVM devices
- **Implementation**:
  - Create test structure in `tests/integration/`
  - Implement real-world test scenarios
  - Add configuration for test PiKVM devices
  - Create documentation for running integration tests
- **Dependencies**: All modules and utilities
- **Expected Outcome**: Integration test suite that validates real-world functionality

### 6.3 CI/CD Pipeline
- **Description**: Set up continuous integration and deployment
- **Implementation**:
  - Create GitHub Actions workflow
  - Configure automated testing
  - Set up linting and syntax checking
  - Add automated build and release process
- **Dependencies**: Unit and integration tests
- **Expected Outcome**: Functional CI/CD pipeline for the collection

## 7. Documentation

### 7.1 Module Documentation
- **Description**: Create comprehensive documentation for all modules
- **Implementation**:
  - Document all parameters and return values
  - Add usage examples
  - Create troubleshooting guides
  - Document limitations and requirements
- **Dependencies**: All modules
- **Expected Outcome**: Complete module documentation

### 7.2 Role Documentation
- **Description**: Create documentation for all roles
- **Implementation**:
  - Document all variables and defaults
  - Add usage examples
  - Create requirement specifications
  - Document integration points
- **Dependencies**: All roles
- **Expected Outcome**: Complete role documentation

### 7.3 Best Practices Guide
- **Description**: Create guide for best practices when using the collection
- **Implementation**:
  - Document security considerations
  - Add performance optimization tips
  - Create integration guidance
  - Add real-world usage scenarios
- **Dependencies**: All collection components
- **Expected Outcome**: Comprehensive best practices guide

## 8. Future Extensions

### 8.1 Additional Modules Planning
- **Description**: Plan for additional modules beyond initial scope
- **Implementation**:
  - Identify additional API endpoints to leverage
  - Document extension points
  - Create development guidelines for new modules
- **Dependencies**: Complete initial implementation
- **Expected Outcome**: Roadmap for future module development

### 8.2 Integration Extensions
- **Description**: Plan for integration with other Ansible collections
- **Implementation**:
  - Identify potential integration points
  - Document cross-collection workflows
  - Create example integration playbooks
- **Dependencies**: Complete initial implementation
- **Expected Outcome**: Integration roadmap and examples

### 8.3 Advanced Features
- **Description**: Plan for advanced features and optimizations
- **Implementation**:
  - Identify performance optimization opportunities
  - Plan for concurrent operations
  - Document advanced usage patterns
- **Dependencies**: Complete initial implementation
- **Expected Outcome**: Roadmap for advanced features
