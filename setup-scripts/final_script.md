Of course. The bash script has been eliminated, and its bootstrap logic is now fully integrated into the Python application. The script is now a self-contained solution that handles everything from pre-flight checks to final configuration.

Here is the complete, modularized Python application rewritten in a clean, readable markdown format.

### How to Use the New Script

The setup process is now simpler:

1.  **Prerequisites**: On your barebones Arch Linux system, you only need `python` and `git`.

    ```bash
    sudo pacman -Syu --noconfirm python git
    ```

2.  **Download the Application**: Download the `arch_installer` directory containing all the Python files.

3.  **Run the Installer**: From the directory containing the `arch_installer` package, run the main `install.py` module. You must provide the HTTPS URL of your dotfiles repository as a command-line argument.

    ```bash
    # Usage: python -m arch_installer.install <your-dotfiles-git-repo-url>

    # Example:
    python -m arch_installer.install https://github.com/your-username/your-dots-repo.git
    ```

The Python application will now handle all checks, installations, and configurations.

---

### Project Structure

Here is the final file structure. All subsequent code blocks should be saved with the corresponding file names inside the `arch_installer` directory.

```
.
└── arch_installer/
    ├── __init__.py
    ├── install.py         # Main entry point (run this)
    ├── config.py
    ├── ui.py
    ├── packages.py
    ├── utils.py
    └── engine.py
```

---

### The Python Application Files

#### `arch_installer/__init__.py`

_This file can be left empty. Its presence makes the `arch_installer` directory a recognizable Python package._

#### `arch_installer/config.py`

_This file holds global constants and configuration variables, making them easy to manage._

```python
# arch_installer/config.py
import os

# --- Core Configuration ---
LOG_FILE = "arch_setup.log"
USER_HOME = os.path.expanduser("~")
CURRENT_USER = os.getlogin()
DOTFILES_DIR = os.path.join(USER_HOME, ".dots")
```

#### `arch_installer/ui.py`

_This module centralizes all user interface logic, including colored console output and icons._

```python
# arch_installer/ui.py
import logging
import sys
from .config import LOG_FILE

class Colors:
    """Container for ANSI color escape sequences."""
    HEADER, BLUE, GREEN, YELLOW, RED, ENDC, BOLD = "\033[95m", "\033[94m", "\033[92m", "\033[93m", "\033[91m", "\033[0m", "\033[1m"

class Icons:
    """Container for Unicode icons."""
    STEP, INFO, SUCCESS, WARNING, ERROR, PROMPT, FINISH, PACKAGE, DESKTOP = "⚙️", "ℹ️", "✅", "⚠️", "❌", "❓", "🎉", "📦", "🖥️"

def setup_logging() -> None:
    """Configures logging to a file for auditing and debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")]
    )

def print_step(message: str):
    """Prints a formatted header for a major step."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}═══ {Icons.STEP} {message} ═══{Colors.ENDC}")
    logging.info(f"--- STEP: {message} ---")

def print_info(message: str):
    """Prints an informational message."""
    print(f"{Colors.BLUE}{Icons.INFO} {message}{Colors.ENDC}")
    logging.info(message)

def print_success(message: str):
    """Prints a success message."""
    print(f"{Colors.GREEN}{Icons.SUCCESS} {message}{Colors.ENDC}")
    logging.info(f"SUCCESS: {message}")

def print_warning(message: str):
    """Prints a warning message."""
    print(f"{Colors.YELLOW}{Icons.WARNING} {message}{Colors.ENDC}", file=sys.stderr)
    logging.warning(message)

def print_error(message: str):
    """Prints an error message and logs it."""
    print(f"{Colors.RED}{Icons.ERROR} {message}{Colors.ENDC}", file=sys.stderr)
    logging.error(message)
```

#### `arch_installer/utils.py`

_This module provides core utility functions that are used throughout the application._

```python
# arch_installer/utils.py
import subprocess
import os
import logging
import socket
from .ui import print_info, print_error

def execute_command(command: list[str], description: str, cwd: str = None) -> bool:
    """Executes a shell command, allows user interaction, and logs the action."""
    print_info(description)
    logging.info(f"Executing command: {' '.join(command)} in '{cwd or os.getcwd()}'")
    try:
        # Use Popen to allow interactive prompts like sudo passwords
        process = subprocess.Popen(command, text=True, encoding="utf-8", cwd=cwd)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, KeyboardInterrupt) as e:
        error_type = "Command not found" if isinstance(e, FileNotFoundError) else "Command failed"
        if isinstance(e, KeyboardInterrupt): error_type = "Process interrupted by user"
        print_error(f"{error_type}: {' '.join(command)}. Reason: {e}")
        return False

def check_internet_connection() -> bool:
    """Checks for a live internet connection by connecting to a known server."""
    try:
        # Connect to a reliable server (Google's public DNS) on the DNS port
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False
```

#### `arch_installer/packages.py`

_This module cleanly categorizes and provides lists of all software to be installed._

```python
# arch_installer/packages.py
from typing import Set, List

class PackageLists:
    """A centralized place for all package lists, categorized for maintainability."""

    @staticmethod
    def _get_base_packages() -> Set[str]:
        return {"acpid", "amd-ucode", "arch-audit", "btrfs-progs", "boost", "btop", "chrony", "curl", "cmake", "dosfstools", "dbus-python", "downgrade", "efibootmgr", "fdupes", "fastfetch", "fwupd", "gcc", "haveged", "jq", "jitterentropy-rngd", "linux-firmware", "lynis", "logrotate", "libva", "make", "mesa", "meson", "networkmanager", "openssh", "pacman-contrib", "pkgconf", "plymouth", "plocate", "piavpn", "rng-tools", "sysstat", "snapper", "snap-pac", "snap-pac-grub", "sof-firmware", "smartmontools", "texinfo", "unzip", "unrar", "upower", "wget", "xz", "zip", "zstd"}

    @staticmethod
    def _get_hyprland_packages() -> Set[str]:
        return {"adw-gtk-theme", "bibata-cursor-theme", "cliphist", "gnome-themes-extra", "greetd", "greetd-tuigreet", "grim", "gstreamer", "gst-plugin-pipewire", "gst-plugins-bad", "gst-plugins-base", "gst-plugins-good", "gst-plugins-ugly", "gtk-engine-murrine", "hypridle", "hyprland", "hyprlock", "hyprnome", "hyprpaper", "hyprpicker", "hyprpolkitagent", "hyprsunset", "inotify-tools", "kvantum", "kvantum-qt5", "mpv", "nwg-drawer", "nwg-look", "papirus-icon-theme", "pavucontrol", "pipewire", "pipewire-alsa", "pipewire-pulse", "pyprland", "qt5-wayland", "qt5ct", "qt6-wayland", "qt6ct", "rofi-wayland", "sassc", "slurp", "swappy", "swww", "socat", "thunar", "thunar-archive-plugin", "thunar-media-tags-plugin", "thunar-volman", "trash-cli", "tumbler", "uwsm", "wf-recorder", "wireplumber", "xarchiver", "xdg-desktop-portal-hyprland", "xdg-user-dirs", "xdg-user-dirs-gtk", "yazi"}

    @staticmethod
    def _get_caelestia_packages() -> Set[str]:
        return {"caelestia-cli", "quickshell-git", "ddcutil", "brightnessctl", "app2unit", "cava", "bluez-utils", "lm_sensors", "fish", "aubio", "libpipewire", "glibc", "qt6-declarative", "gcc-libs", "power-profiles-daemon", "ttf-material-symbols-variable", "libqalculate"}

    @staticmethod
    def _get_applications() -> Set[str]:
        return {"zathura", "zathura-pdf-poppler", "zen-browser-bin", "zotero", "deluge-gtk", "bleachbit", "bitwarden", "xournalpp"}

    @staticmethod
    def _get_dev_tools() -> Set[str]:
        return {"autoconf", "automake", "cargo", "devtools", "direnv", "emacs-lsp-booster-git", "fd", "fzf", "go", "hspell", "nuspell", "libvoikko", "hunspell", "hunspell-en_us", "imagemagick", "jansson", "neovim", "nodejs", "nodejs-neovim", "npm", "org.freedesktop.secrets", "pkg-config", "poppler", "poppler-glib", "python-neovim", "python-pip", "python-pynvim", "ripgrep", "rust", "tree-sitter-cli", "tree-sitter-bash", "tree-sitter-markdown", "tree-sitter-python", "ttf-jetbrains-mono", "ttf-jetbrains-mono-nerd", "ttf-ubuntu-font-family", "typescript", "wl-clipboard", "yarn"}

    @staticmethod
    def _get_cli_tools() -> Set[str]:
        return {"atuin", "bat", "eza", "starship", "tealdeer", "thefuck", "zoxide", "zsh"}

    @staticmethod
    def _get_graphics_packages() -> Set[str]:
        return {"ffnvcodec-headers", "libva-nvidia-driver", "linux-cachyos-bore-lto-nvidia-open", "nvidia-container-toolkit", "nvidia-utils", "opencl-nvidia", "vulkan-headers", "vulkan-tools", "vulkan-validation-layers", "xf86-video-amdgpu", "xorg-xwayland"}

    @staticmethod
    def _get_container_packages() -> Set[str]:
        return {"aardvark-dns", "boxbuddy", "cockpit", "cockpit-packagekit", "cockpit-podman", "distrobox", "lxd", "netavark", "podman", "podman-docker"}

    @staticmethod
    def _get_security_packages() -> Set[str]:
        return {"git", "git-delta", "git-lfs", "gnome-keyring", "lazygit", "libsecret", "seahorse", "apparmor", "apparmor.d-git", "audit", "python-notify2", "python-psutil"}

    @classmethod
    def get_all(cls) -> List[str]:
        """Combines all package categories into a single, sorted list."""
        all_packages = set.union(
            cls._get_base_packages(), cls._get_hyprland_packages(), cls._get_caelestia_packages(),
            cls._get_applications(), cls._get_dev_tools(), cls._get_cli_tools(),
            cls._get_graphics_packages(), cls._get_container_packages(), cls._get_security_packages()
        )
        return sorted(list(all_packages))
```

#### `arch_installer/engine.py`

_This is the core of the application, containing the `SetupManager` class with all the installation and configuration logic._

```python
# arch_installer/engine.py
import os
import shutil
import tempfile
from typing import List, Tuple

from .config import USER_HOME, CURRENT_USER, DOTFILES_DIR
from .ui import (print_step, print_info, print_success, print_warning, print_error, Icons, Colors)
from .utils import execute_command, check_internet_connection
from .packages import PackageLists

class SetupManager:
    """Encapsulates all setup, bootstrap, and configuration logic."""
    def __init__(self):
        self.failed_steps: List[str] = []

    def _record_failure(self, description: str):
        self.failed_steps.append(description)

    def run_bootstrap_checks(self, dotfiles_url: str) -> bool:
        """Runs all pre-flight checks before main installation begins."""
        print_step("Running Bootstrap Checks")
        checks = {
            "Root user check": lambda: os.geteuid() != 0,
            "Internet connection": check_internet_connection,
            "`git` command available": lambda: shutil.which("git") is not None
        }
        for desc, check_func in checks.items():
            if not check_func():
                print_error(f"Bootstrap check failed: {desc}. Please resolve the issue and try again.")
                return False
            print_success(f"{desc}: OK")

        # Clone dotfiles
        print_info(f"Cloning dotfiles from '{dotfiles_url}' into '{DOTFILES_DIR}'...")
        if os.path.isdir(DOTFILES_DIR):
            print_warning(f"Dotfiles directory '{DOTFILES_DIR}' already exists. Skipping clone.")
        elif not execute_command(["git", "clone", dotfiles_url, DOTFILES_DIR], "Cloning dotfiles repository."):
            print_error("Failed to clone dotfiles repository.")
            return False

        return True

    def ensure_yay_installed(self) -> bool:
        """Checks for yay and installs it from the AUR if not present."""
        if shutil.which("yay"):
            print_success("'yay' is already installed.")
            return True

        print_warning("'yay' is not installed. Attempting to install it from the AUR...")
        print_step(f"{Icons.PACKAGE} Installing AUR Helper (yay)")

        if not execute_command(["sudo", "pacman", "-S", "--needed", "--noconfirm", "base-devel"], "Installing 'base-devel' for AUR helper installation."):
            print_error("Failed to install build dependencies. Cannot proceed.")
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            if not execute_command(["git", "clone", "https://aur.archlinux.org/yay-bin.git", tmpdir], "Cloning 'yay-bin' repository from AUR."): return False
            if not execute_command(["makepkg", "-si", "--noconfirm"], "Running 'makepkg -si' to build and install 'yay'.", cwd=tmpdir): return False

        if shutil.which("yay"): print_success("'yay' has been successfully installed."); return True
        else: print_error("Installation failed. 'yay' command not found in PATH."); return False

    def run_package_installation(self, extra_packages: List[str]) -> bool:
        """Installs all system packages using yay."""
        print_step("Installing System Packages")
        packages_to_install = PackageLists.get_all()
        if extra_packages:
            print_info(f"Adding {len(extra_packages)} hardware-specific packages.")
            packages_to_install = sorted(list(set(packages_to_install).union(extra_packages)))

        print_info(f"Found {len(packages_to_install)} unique packages to install.")
        return execute_command(["yay", "-S", "--needed", "--noconfirm"] + packages_to_install, "Running 'yay' to install all packages.")

    def run_all_configurations(self, asus_services: List[str]):
        """Runs all post-install configuration steps."""
        print_step("Applying System and User Configurations")
        self._configure_caelestia()
        self._configure_symlinks()
        self._configure_system_services(asus_services)
        self._configure_user_services()
        self._configure_git()
        self._configure_npm()
        self._configure_shell()

    def _configure_caelestia(self):
        """Clones Caelestia config and compiles/installs its helper binary."""
        print_info(f"{Icons.DESKTOP} Configuring Caelestia Desktop Shell")
        config_dir = os.path.join(USER_HOME, ".config", "quickshell")
        if not os.path.exists(config_dir):
            if not execute_command(["git", "clone", "https://github.com/caelestia-dots/shell.git", config_dir], "Cloning Caelestia shell configuration."):
                self._record_failure("Clone Caelestia config"); return

        source_file = os.path.join(config_dir, "cxx", "beat_detector.cpp")
        if not os.path.exists(source_file):
            print_warning(f"Caelestia source file not found at '{source_file}', skipping compilation.")
            return

        output_file = os.path.join(config_dir, "beat_detector")
        cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-I/usr/include/pipewire-0.3", "-I/usr/include/spa-0.2", "-I/usr/include/aubio", "-o", output_file, source_file, "-lpipewire-0.3", "-laubio"]
        if not execute_command(cmd, "Compiling Caelestia beat detector utility.", cwd=config_dir):
            self._record_failure("Compile Caelestia beat detector"); return

        dest_dir = "/usr/lib/caelestia"
        if not execute_command(["sudo", "mkdir", "-p", dest_dir], f"Creating destination directory '{dest_dir}'."): self._record_failure("Create Caelestia lib dir"); return
        if not execute_command(["sudo", "mv", output_file, os.path.join(dest_dir, 'beat_detector')], "Installing compiled binary."): self._record_failure("Install Caelestia binary")

    def _configure_symlinks(self):
        """Creates symbolic links for custom scripts from the dotfiles repo."""
        base_dir = os.path.join(DOTFILES_DIR, "arch-scripts", "bin")
        if not os.path.isdir(base_dir):
            self._record_failure(f"Dotfiles script directory not found, cannot create symlinks: {base_dir}")
            return

        for script in ["cliphist-rofi", "hyprlauncher", "hyprrunner", "hyprterm", "hyprtheme"]:
            src, dest = os.path.join(base_dir, script), f"/usr/local/bin/{script}"
            if not os.path.lexists(dest) and os.path.exists(src):
                if not execute_command(["sudo", "ln", "-s", src, dest], f"Linking '{script}'"):
                    self._record_failure(f"Link {script}")

    def _configure_system_services(self, extra_services: List[str]):
        """Configures and enables system-wide services."""
        services = {"acpid.service", "apparmor.service", "auditd.service", "chronyd.service", "cockpit.socket", "grub-btrfsd.service", "haveged.service", "jitterentropy-rngd.service", "lxd.service", "NetworkManager.service", "piavpn.service", "rngd.service", "sshd.service", "sysstat.service", "power-profiles-daemon.service"}
        services.update(extra_services)
        if not execute_command(["sudo", "systemctl", "enable"] + sorted(list(services)), "Enabling system services."):
            self._record_failure("Enable system services")

    def _configure_user_services(self):
        """Configures and enables user-specific services."""
        services = {"hypridle.service", "hyprpaper.service", "hyprpolkitagent.service", "hyprsunset.service", "pipewire.service", "pipewire.socket", "pipewire-pulse.service", "pipewire-pulse.socket", "uwsm.service", "wireplumber.service"}
        if not execute_command(["systemctl", "--user", "enable"] + sorted(list(services)), "Enabling user services."):
            self._record_failure("Enable user services")

    def _configure_git(self):
        """Configures global Git settings."""
        configs = [
            (["git", "config", "--global", "user.name", "aahsnr"], "Configuring Git user name."),
            (["git", "config", "--global", "user.email", "ahsanur041@proton.me"], "Configuring Git user email."),
            (["git", "config", "--global", "credential.helper", "/usr/lib/git-core/git-credential-libsecret"], "Configuring Git credential helper."),
        ]
        for cmd, desc in configs:
            if not execute_command(cmd, desc): self._record_failure(desc)

    def _configure_npm(self):
        """Configures NPM global directory."""
        npm_dir = os.path.join(USER_HOME, ".npm-global")
        os.makedirs(npm_dir, exist_ok=True)
        if not execute_command(["npm", "config", "set", "prefix", npm_dir], "Setting NPM global prefix."):
            self._record_failure("Configure NPM prefix")

    def _configure_shell(self):
        """Changes the default shell for the user to Zsh."""
        zsh_path = shutil.which("zsh")
        if zsh_path:
            if not execute_command(["sudo", "chsh", "-s", zsh_path, CURRENT_USER], f"Changing shell to Zsh for user '{CURRENT_USER}'." ):
                self._record_failure("Change default shell")
        else:
            self._record_failure("Zsh not found in PATH, cannot set as default shell.")

    def prompt_for_asus_setup(self) -> Tuple[List[str], List[str]]:
        """Prompts for and runs optional Asus-specific setup."""
        print_step("Asus ROG Laptop Configuration (Optional)")
        prompt = f"{Colors.YELLOW}{Icons.PROMPT} Do you want to run the Asus-specific setup? [y/N]: {Colors.ENDC}"
        if input(prompt).lower().strip() != "y":
            print_info("Skipping Asus setup.")
            return [], []

        print_info("Proceeding with Asus setup...")
        key_id = "8F654886F17D497FEFE3DB448B15A6B0E9A3FA35"
        if not execute_command(["sudo", "pacman-key", "--recv-keys", key_id], "Receiving g14 repo key.") or \
           not execute_command(["sudo", "pacman-key", "--lsign-key", key_id], "Locally signing g14 repo key."):
            return [], []

        try:
            with open("/etc/pacman.conf", "r+", encoding="utf-8") as f:
                content = f.read()
                if "[g14]" not in content:
                    f.write("\n[g14]\nServer = https://arch.asus-linux.org\n")
                    print_success("Added [g14] repo to pacman.conf.")
        except IOError as e:
            print_error(f"Could not access /etc/pacman.conf: {e}"); return [],[]

        execute_command(["sudo", "pacman", "-Syyu"], "Synchronizing package databases.")
        return (["asusctl", "supergfxctl", "switcheroo-control", "rog-control-center"], ["supergfxd.service", "switcheroo-control.service"])
```

#### `arch_installer/install.py`

_This is the main entry point for the entire application. It parses arguments and orchestrates the setup process using the `SetupManager`._

```python
# arch_installer/install.py
import sys
import argparse
from arch_installer.ui import (setup_logging, print_step, print_success, print_warning, print_error, Icons, Colors)
from arch_installer.engine import SetupManager
from arch_installer.utils import execute_command

def main() -> None:
    """Main function to parse arguments and orchestrate the setup process."""
    parser = argparse.ArgumentParser(description="A comprehensive Python script to automate the setup of an Arch Linux system.")
    parser.add_argument("dotfiles_url", help="The HTTPS URL of the dotfiles repository to clone.")
    args = parser.parse_args()

    setup_logging()
    print(f"{Colors.BOLD}--- Arch Linux Setup Script (v10 - Self-Contained) ---{Colors.ENDC}")

    manager = SetupManager()

    # --- Bootstrap Phase ---
    if not manager.run_bootstrap_checks(args.dotfiles_url):
        print_error("Bootstrap phase failed. Aborting installation."); sys.exit(1)

    print_step("Acquiring Administrator Privileges")
    if not execute_command(["sudo", "-v"], "Caching sudo credentials for the duration of the script."):
        print_error("Could not acquire sudo privileges. Aborting."); sys.exit(1)

    if not manager.ensure_yay_installed():
        print_error("Failed to install 'yay', which is required. Aborting."); sys.exit(1)

    # --- Main Workflow ---
    asus_packages, asus_services = manager.prompt_for_asus_setup()

    if not manager.run_package_installation(asus_packages):
        print_error("Package installation failed. Aborting."); sys.exit(1)

    manager.run_all_configurations(asus_services)

    # --- Final Summary ---
    print_step(f"{Icons.FINISH} Setup Complete!")
    if not manager.failed_steps:
        print_success("System setup finished successfully!")
    else:
        print_warning(f"System setup finished with {len(manager.failed_steps)} error(s).")
        print_warning("The following configuration steps failed:")
        for failure in manager.failed_steps:
            print(f"  - {failure}")
        print_warning(f"Please review the output and check the log file for details.")
        sys.exit(1)

    print(f"\n{Colors.BLUE}{Icons.INFO} A system reboot is highly recommended to apply all changes.{Colors.ENDC}")

if __name__ == "__main__":
    main()
```
