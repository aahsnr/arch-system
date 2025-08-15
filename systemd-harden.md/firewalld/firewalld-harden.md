# Final Bash Script to Reliably Harden Firewalld

This script creates a systemd override file that applies robust security settings while ensuring `firewalld` has the necessary permissions for logging and runtime operations. This is the recommended, update-safe method.

```bash
#!/bin/bash

# This script hardens the firewalld systemd service on Arch Linux using the
# recommended, update-safe override method.
#
# It applies a strong security profile while ensuring smooth operation by
# providing dedicated writable directories for logs and runtime state,
# which is necessary when using strong filesystem protections.

set -euo pipefail

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Please use sudo." >&2
  exit 1
fi

# Define the override directory and file paths
OVERRIDE_DIR="/etc/systemd/system/firewalld.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/hardening.conf"

echo "Creating systemd override directory for firewalld..."
mkdir -p "$OVERRIDE_DIR"

# Create the hardening override file content.
# This configuration is designed for both strong security and stability.
cat > "$OVERRIDE_FILE" <<EOF
[Service]
# --- Directives for Stability & Functionality ---

# Give firewalld a writable directory for its logs under /var/log/.
# This is the correct way to solve the "Read-only file system" error for logs.
LogsDirectory=firewalld

# Give firewalld a writable directory for runtime state under /run/.
# This prevents issues with state files, sockets, or PID files.
RuntimeDirectory=firewalld

# --- Security Hardening Directives ---

# Restrict the service's capabilities to the required minimum for managing networks.
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW

# Filesystem Protections: Mount key directories as read-only.
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true

# Kernel Protections: Prevent the service from modifying the running kernel.
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Privilege Escalation Prevention.
NoNewPrivileges=true

# Restrict network protocol families. AF_NETLINK is crucial for communication
# with the kernel's netfilter subsystem.
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK

# Disallow creation of new namespaces.
RestrictNamespaces=true

# Apply a system call filter tailored for network services.
SystemCallFilter=@network

# Enforce other memory and process security settings.
MemoryDenyWriteExecute=true
LockPersonality=true
UMask=0077
EOF

echo "Successfully created hardening override file at ${OVERRIDE_FILE}"

# Reload the systemd daemon to read the new override file
echo "Reloading the systemd daemon..."
systemctl daemon-reload

# Restart firewalld to apply the new hardened settings
echo "Restarting firewalld..."
systemctl restart firewalld

echo ""
echo "-----------------------------------------------------"
echo "Firewalld service has been successfully hardened."
echo "The service should be active and running smoothly."
echo "-----------------------------------------------------"
echo ""
echo "To verify the changes, run: systemctl cat firewalld"
echo "You will see the original service file followed by your override configuration."
echo ""
echo "To check the service status, run: systemctl status firewalld"

exit 0
```

## How to Use the Script

1.  Save the script to a file (e.g., `harden_firewalld_stable.sh`).
2.  Make it executable: `chmod +x harden_firewalld_stable.sh`
3.  Run it with root privileges: `sudo ./harden_firewalld_stable.sh`

## How to Revert the Changes

Reverting is safe and easy. Simply remove the override file and restart the service to return to the default Arch Linux configuration.

```bash
sudo rm /etc/systemd/system/firewalld.service.d/hardening.conf
sudo systemctl daemon-reload
sudo systemctl restart firewalld
```
