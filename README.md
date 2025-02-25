# Ansible Collection for PiKVM

[![Ansible Galaxy](https://img.shields.io/badge/ansible-galaxy-blue.svg)](https://galaxy.ansible.com/nsys/pikvm)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

An Ansible collection for managing and automating PiKVM devices. This collection leverages the PiKVM API to provide Ansible modules, roles, and playbooks for controlling and monitoring PiKVM devices.

## Features

This collection enables you to:

- **Manage system information**: Retrieve system info and logs
- **Control ATX power**: Power on/off, reset, and manage PC power state
- **Manage Mass Storage Drive (MSD)**: Upload, connect, disconnect, and manage drive images
- **Control GPIO channels**: Manage GPIO state, switching, and pulsing
- **Take snapshots**: Capture screen images and OCR text
- **Send keyboard input**: Automate keyboard actions and input via WebSocket

## Requirements

- Ansible 2.10 or higher
- Python 3.9 or higher
- Network access to your PiKVM devices

## Installation

### From Ansible Galaxy

```bash
ansible-galaxy collection install nsys.pikvm
```

### From GitHub

```bash
git clone https://github.com/username/ansible-collection-pikvm.git
cd ansible-collection-pikvm
ansible-galaxy collection build
ansible-galaxy collection install nsys-pikvm-*.tar.gz
```

## Modules

### pikvm_info

Get system information from PiKVM device.

```yaml
- name: Get PiKVM system info
  namespace.pikvm.pikvm_info:
    hostname: 192.168.1.10
    username: admin
    password: password
  register: pikvm_info
```

### pikvm_atx

Control ATX power operations.

```yaml
- name: Power on server
  namespace.pikvm.pikvm_atx:
    hostname: 192.168.1.10
    username: admin
    password: password
    action: on
```

### pikvm_msd

Manage Mass Storage Drive operations.

```yaml
- name: Upload and connect ISO image
  namespace.pikvm.pikvm_msd:
    hostname: 192.168.1.10
    username: admin
    password: password
    image_path: /path/to/image.iso
    state: connected
    media_type: cdrom
```

### pikvm_gpio

Control GPIO channels.

```yaml
- name: Control GPIO channel
  namespace.pikvm.pikvm_gpio:
    hostname: 192.168.1.10
    username: admin
    password: password
    channel: 1
    state: on
```

### pikvm_snapshot

Take screen snapshots with optional OCR.

```yaml
- name: Capture screen with OCR
  namespace.pikvm.pikvm_snapshot:
    hostname: 192.168.1.10
    username: admin
    password: password
    path: /tmp/screenshots
    filename: boot_screen.txt
    ocr: true
  register: ocr_result
```

### pikvm_keyboard

Send keyboard input to target.

```yaml
- name: Send keyboard input
  namespace.pikvm.pikvm_keyboard:
    hostname: 192.168.1.10
    username: admin
    password: password
    text: "root\n"  # Send 'root' followed by Enter
```

## Roles

### pikvm_setup

Configure a PiKVM device with standard settings.

```yaml
- name: Configure PiKVM
  include_role:
    name: nsys.pikvm.pikvm_setup
  vars:
    pikvm_hostname: 192.168.1.10
    pikvm_username: admin
    pikvm_password: password
```

### pikvm_boot_iso

Boot a server from an ISO image using PiKVM.

```yaml
- name: Boot from ISO
  include_role:
    name: nsys.pikvm.pikvm_boot_iso
  vars:
    pikvm_hostname: 192.168.1.10
    pikvm_username: admin
    pikvm_password: password
    iso_path: /path/to/installer.iso
```

## Example Playbooks

### Basic Power Control

```yaml
---
- name: Power cycle server with PiKVM
  hosts: localhost
  gather_facts: false
  collections:
    - nsys.pikvm
  
  tasks:
    - name: Power off server
      pikvm_atx:
        hostname: 192.168.1.10
        username: admin
        password: password
        action: off
      
    - name: Wait for server to power off
      pause:
        seconds: 10
      
    - name: Power on server
      pikvm_atx:
        hostname: 192.168.1.10
        username: admin
        password: password
        action: on
```

### OS Installation

```yaml
---
- name: Install OS using PiKVM
  hosts: localhost
  gather_facts: false
  collections:
    - namespace.pikvm
  
  tasks:
    - name: Upload ISO image
      pikvm_msd:
        hostname: 192.168.1.10
        username: admin
        password: password
        image_path: /path/to/os_image.iso
        state: connected
        media_type: cdrom
      
    - name: Reboot target into BIOS
      pikvm_atx:
        hostname: 192.168.1.10
        username: admin
        password: password
        action: reset_hard
      
    - name: Press F12 for boot menu
      pikvm_keyboard:
        hostname: 192.168.1.10
        username: admin
        password: password
        text: "<F12>"
      
    # Additional tasks to select boot device and automate installation
```

## Authentication with 2FA

For PiKVM instances with 2FA enabled, you'll need to handle the TOTP authentication. Example:

```yaml
- name: Get PiKVM info with 2FA
  namespace.pikvm.pikvm_info:
    hostname: 192.168.1.10
    username: admin
    password: "{{ password }}"
    totp_secret: "{{ totp_secret }}"  # From /etc/kvmd/totp.secret
```

## Security Considerations

- Store credentials securely using Ansible Vault
- Consider using dedicated service accounts for automation
- Limit network access to PiKVM devices

## License

GPL-3.0-or-later

## Author Information

ai-working-group

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
