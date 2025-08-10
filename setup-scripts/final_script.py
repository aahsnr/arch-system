#!/usr/bin/env python3.13
# -*- coding: utf-8 -*-

"""
A comprehensive Python script to automate the setup of an Arch Linux system.

This script consolidates multiple setup scripts into a single, robust, and
user-friendly tool. It handles package installation, system/user service
management, dotfile linking, and optional hardware-specific configurations.

Version 5 Improvements:
- Automatically installs 'yay-bin' from the AUR if 'yay' is not found.
- Installs 'base-devel' and 'git' as prerequisites for building AUR packages.
- Added a dedicated 'Icons' class for Unicode symbols.
- Integrated color-coded icons into all console output for improved readability.
- The core logic remains robust and unchanged from the previous version.
"""

import subprocess
import logging
import sys
import os
import shutil
import requests
import tempfile
from typing import List, Set, Tuple

# --- Configuration ---
LOG_FILE = "arch_setup.log"
USER_HOME = os.path.expanduser("~")
CURRENT_USER = os.getlogin()


# --- ANSI Color Codes for Unicode Output ---
class Colors:
    """Container for ANSI color escape sequences for formatted output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


# --- Unicode Icons ---
class Icons:
    """Container for Unicode icons for different message types."""

    STEP = "⚙️"
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    PROMPT = "❓"
    FINISH = "🎉"
    PACKAGE = "📦"


# --- Logger and Console Output Setup ---
def setup_logging() -> None:
    """Configures logging to a file for auditing and debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")],
    )


def print_step(message: str) -> None:
    """Prints a formatted header for a major step."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}═══ {Icons.STEP} {message} ═══{Colors.ENDC}")
    logging.info(f"--- STEP: {message} ---")


def print_info(message: str) -> None:
    """Prints an informational message."""
    print(f"{Colors.BLUE}{Icons.INFO} {message}{Colors.ENDC}")
    logging.info(message)


def print_success(message: str) -> None:
    """Prints a success message."""
    print(f"{Colors.GREEN}{Icons.SUCCESS} {message}{Colors.ENDC}")
    logging.info(f"SUCCESS: {message}")


def print_warning(message: str) -> None:
    """Prints a warning message."""
    print(f"{Colors.YELLOW}{Icons.WARNING} {message}{Colors.ENDC}", file=sys.stderr)
    logging.warning(message)


def print_error(message: str) -> None:
    """Prints an error message and logs it."""
    print(f"{Colors.RED}{Icons.ERROR} {message}{Colors.ENDC}", file=sys.stderr)
    logging.error(message)


# --- Command Execution Utility ---
def execute_command(command: List[str], description: str) -> bool:
    """
    Executes a shell command and handles its success or failure.
    Allows for full interactivity with prompts (sudo, yay, etc.).
    """
    print_info(description)
    logging.info(f"Executing command: {' '.join(command)}")
    try:
        # Using Popen to allow for interactive prompts like sudo passwords
        process = subprocess.Popen(command, text=True, encoding="utf-8")
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        return True
    except FileNotFoundError:
        print_error(
            f"Command not found: '{command[0]}'. Please ensure it's in your PATH."
        )
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}. See output above.")
        return False
    except KeyboardInterrupt:
        print_error("\nProcess interrupted by user.")
        return False


# --- Setup Modules ---


def get_all_packages() -> List[str]:
    """Gathers and deduplicates all packages required for the setup."""
    all_packages: Set[str] = set(
        [
            # Base & Tools
            "acpid",
            "amd-ucode",
            "arch-audit",
            "btrfs-progs",
            "boost",
            "btop",
            "chrony",
            "curl",
            "cmake",
            "dosfstools",
            "dbus-python",
            "downgrade",
            "efibootmgr",
            "fdupes",
            "fastfetch",
            "fwupd",
            "gcc",
            "haveged",
            "jq",
            "jitterentropy-rngd",
            "linux-firmware",
            "lynis",
            "logrotate",
            "libva",
            "make",
            "mesa",
            "meson",
            "networkmanager",
            "openssh",
            "pacman-contrib",
            "pkgconf",
            "plymouth",
            "python-pam",
            "python-requests",
            "plocate",
            "piavpn",
            "rng-tools",
            "sysstat",
            "snapper",
            "snap-pac",
            "snap-pac-grub",
            "sof-firmware",
            "smartmontools",
            "texinfo",
            "unzip",
            "unrar",
            "upower",
            "wget",
            "xz",
            "zip",
            "zstd",
            "pyalpm",
            # Apps
            "zathura",
            "zathura-pdf-poppler",
            "zen-browser-bin",
            "zotero",
            "deluge-gtk",
            "bleachbit",
            "bitwarden",
            "xournalpp",
            # Desktop Environment
            "adw-gtk-theme",
            "bibata-cursor-theme",
            "brightnessctl",
            "cliphist",
            "gnome-themes-extra",
            "greetd",
            "greetd-tuigreet",
            "grim",
            "gstreamer",
            "gst-plugin-pipewire",
            "gst-plugins-bad",
            "gst-plugins-base",
            "gst-plugins-good",
            "gst-plugins-ugly",
            "gtk-engine-murrine",
            "hypridle",
            "hyprland",
            "hyprlock",
            "hyprnome",
            "hyprpaper",
            "hyprpicker",
            "hyprpolkitagent",
            "hyprsunset",
            "inotify-tools",
            "kvantum",
            "kvantum-qt5",
            "kvantum-theme-catppuccin-git",
            "mpv",
            "nwg-drawer",
            "nwg-look",
            "papirus-icon-theme",
            "papirus-folders-catppuccin-git",
            "pavucontrol",
            "pipewire",
            "pipewire-alsa",
            "pipewire-pulse",
            "pyprland",
            "qt5-wayland",
            "qt5ct",
            "qt6-wayland",
            "qt6ct",
            "rofi-wayland",
            "sassc",
            "slurp",
            "swappy",
            "swww",
            "socat",
            "thunar",
            "thunar-archive-plugin",
            "thunar-media-tags-plugin",
            "thunar-volman",
            "trash-cli",
            "tumbler",
            "uwsm",
            "wf-recorder",
            "wireplumber",
            "xarchiver",
            "xdg-desktop-portal-hyprland",
            "xdg-user-dirs",
            "xdg-user-dirs-gtk",
            "yazi",
            # Editors & Dev Tools
            "autoconf",
            "automake",
            "cargo",
            "devtools",
            "direnv",
            "emacs-lsp-booster-git",
            "emacs-wayland",
            "fd",
            "fzf",
            "go",
            "hunspell",
            "hunspell-en_us",
            "imagemagick",
            "jansson",
            "marksman",
            "markdownlint-cli",
            "miniconda3",
            "neovim",
            "nodejs",
            "nodejs-neovim",
            "npm",
            "org.freedesktop.secrets",
            "pkg-config",
            "plantuml",
            "poppler",
            "poppler-glib",
            "pyright",
            "python-neovim",
            "python-pip",
            "python-pipx",
            "python-pynvim",
            "ripgrep",
            "rust",
            "tree-sitter-cli",
            "ttf-jetbrains-mono",
            "ttf-jetbrains-mono-nerd",
            "ttf-ubuntu-font-family",
            "typescript",
            "wl-clipboard",
            "yarn",
            # Shell & CLI
            "atuin",
            "bat",
            "eza",
            "starship",
            "tealdeer",
            "thefuck",
            "zoxide",
            "zsh",
            # Graphics
            "ffnvcodec-headers",
            "libva-nvidia-driver",
            "linux-cachyos-bore-lto-nvidia-open",
            "nvidia-container-toolkit",
            "nvidia-utils",
            "opencl-nvidia",
            "vulkan-headers",
            "vulkan-tools",
            "vulkan-validation-layers",
            "xf86-video-amdgpu",
            "xorg-xwayland",
            # Containers
            "aardvark-dns",
            "boxbuddy",
            "cockpit",
            "cockpit-packagekit",
            "cockpit-podman",
            "distrobox",
            "lxd",
            "netavark",
            "podman",
            "podman-docker",
            # Git & Secrets
            "git",
            "git-delta",
            "git-lfs",
            "gnome-keyring",
            "lazygit",
            "libsecret",
            "seahorse",
            # AppArmor
            "apparmor",
            "apparmor.d-git",
            "audit",
            "python-notify2",
            "python-psutil",
        ]
    )
    return sorted(list(all_packages))


def _install_yay() -> bool:
    """
    Installs the 'yay-bin' package from the AUR if 'yay' is not found.
    This function handles the entire process of cloning, building, and installing.
    """
    print_step(f"{Icons.PACKAGE} Installing AUR Helper (yay)")

    # Ensure build tools are present
    if not execute_command(
        ["sudo", "pacman", "-S", "--needed", "--noconfirm", "base-devel", "git"],
        "Installing 'base-devel' and 'git' for AUR helper installation.",
    ):
        print_error(
            "Failed to install build dependencies. Cannot proceed with 'yay' installation."
        )
        return False

    # Create a temporary directory for the build
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            print_info(f"Cloning 'yay-bin' into temporary directory: {tmpdir}")
            os.chdir(tmpdir)
            if not execute_command(
                ["git", "clone", "https://aur.archlinux.org/yay-bin.git"],
                "Cloning 'yay-bin' repository from AUR.",
            ):
                return False

            os.chdir("yay-bin")
            print_info(
                "Building and installing 'yay-bin'. This may require your password."
            )

            # Use makepkg to build and install. '-si' will sync dependencies and install.
            if not execute_command(
                ["makepkg", "-si", "--noconfirm"],
                "Running 'makepkg -si' to build and install.",
            ):
                print_error("'makepkg' failed. Could not install 'yay'.")
                return False

        except Exception as e:
            print_error(f"An unexpected error occurred during 'yay' installation: {e}")
            return False
        finally:
            os.chdir(original_dir)  # Ensure we change back to the original directory

    # Verify installation
    if shutil.which("yay"):
        print_success("'yay' has been successfully installed.")
        return True
    else:
        print_error("Installation complete, but 'yay' command not found in PATH.")
        return False


def run_package_installation(extra_packages: List[str]) -> bool:
    """Installs all collected packages using yay."""
    print_step("Installing System Packages")
    packages_to_install = get_all_packages()

    if extra_packages:
        print_info(f"Adding {len(extra_packages)} hardware-specific packages.")
        packages_to_install.extend(extra_packages)
        packages_to_install = sorted(list(set(packages_to_install)))

    print_info(f"Found {len(packages_to_install)} unique packages to install.")
    # Add --needed to avoid reinstalling packages that are already up-to-date
    yay_command = ["yay", "-S", "--needed"] + packages_to_install

    if execute_command(
        yay_command, "Running 'yay' to install all packages. This may take a long time."
    ):
        print_success("Package installation completed.")
        return True
    else:
        print_error("Package installation failed. Aborting.")
        return False


def run_all_configurations(asus_services: List[str]) -> List[str]:
    """Runs all post-install configuration steps and returns a list of failures."""
    print_step("Applying System and User Configurations")
    failed_steps = []
    failed_steps.extend(_configure_symlinks())
    failed_steps.extend(_configure_system_services(asus_services))
    failed_steps.extend(_configure_user_services())
    failed_steps.extend(_configure_git())
    failed_steps.extend(_configure_npm())
    failed_steps.extend(_configure_shell())
    return failed_steps


# --- Configuration Helper Functions (Internal) ---


def _configure_symlinks() -> List[str]:
    """Creates symbolic links for custom scripts. Returns failures."""
    failures = []
    print_info("Creating symbolic links for custom scripts...")
    base_dir = os.path.join(USER_HOME, ".dots", "arch-scripts", "bin")
    scripts = ["cliphist-rofi", "hyprlauncher", "hyprrunner", "hyprterm", "hyprtheme"]
    for script in scripts:
        src = os.path.join(base_dir, script)
        dest = f"/usr/local/bin/{script}"
        desc = f"Linking '{script}' to '{dest}'"
        if not os.path.exists(src):
            print_warning(f"Source file not found, skipping: {src}")
            continue
        if os.path.lexists(dest):
            print_info(f"Symlink already exists: {dest}")
            continue
        if not execute_command(["sudo", "ln", "-s", src, dest], desc):
            failures.append(desc)
    return failures


def _configure_system_services(extra_services: List[str]) -> List[str]:
    """Configures system-wide services. Returns failures."""
    failures = []
    print_info("Configuring system-wide services...")
    services_to_enable = {
        "acpid.service",
        "apparmor.service",
        "auditd.service",
        "chronyd.service",
        "cockpit.socket",
        "grub-btrfsd.service",
        "haveged.service",
        "jitterentropy-rngd.service",
        "lxd.service",
        "NetworkManager.service",
        "piavpn.service",
        "rngd.service",
        "sshd.service",
        "sysstat.service",
    }
    services_to_enable.update(extra_services)
    commands = [
        (
            ["sudo", "systemctl", "set-default", "graphical.target"],
            "Setting default target to graphical.",
        ),
        (
            ["sudo", "systemctl", "enable", "--now"] + sorted(list(services_to_enable)),
            "Enabling system services.",
        ),
        (
            ["sudo", "systemctl", "disable", "greetd.service"],
            "Disabling greetd service.",
        ),
    ]
    for cmd, desc in commands:
        if not execute_command(cmd, desc):
            failures.append(desc)
    return failures


def _configure_user_services() -> List[str]:
    """Configures user-specific services. Returns failures."""
    print_info("Configuring user services...")
    user_services = {
        "hypridle.service",
        "hyprpaper.service",
        "hyprpolkitagent.service",
        "hyprsunset.service",
        "pipewire.service",
        "pipewire.socket",
        "pipewire-pulse.service",
        "pipewire-pulse.socket",
        "uwsm.service",
        "wireplumber.service",
    }
    desc = "Enabling user systemd services."
    cmd = ["systemctl", "--user", "enable", "--now"] + sorted(list(user_services))
    return [desc] if not execute_command(cmd, desc) else []


def _configure_git() -> List[str]:
    """Configures global Git settings. Returns failures."""
    print_info("Configuring Git...")
    failures = []
    commands = [
        (
            ["git", "config", "--global", "user.name", "aahsnr"],
            "Configuring Git user name.",
        ),
        (
            ["git", "config", "--global", "user.email", "ahsanur041@proton.me"],
            "Configuring Git user email.",
        ),
        (
            [
                "git",
                "config",
                "--global",
                "credential.helper",
                "/usr/lib/git-core/git-credential-libsecret",
            ],
            "Configuring Git credential helper.",
        ),
    ]
    for cmd, desc in commands:
        if not execute_command(cmd, desc):
            failures.append(desc)
    return failures


def _configure_npm() -> List[str]:
    """Configures NPM global directory. Returns failures."""
    print_info("Configuring NPM...")
    npm_global_dir = os.path.join(USER_HOME, ".npm-global")
    os.makedirs(npm_global_dir, exist_ok=True)
    desc = "Setting NPM global prefix."
    cmd = ["npm", "config", "set", "prefix", npm_global_dir]
    return [desc] if not execute_command(cmd, desc) else []


def _configure_shell() -> List[str]:
    """Changes the default shell for the user. Returns failures."""
    print_info("Configuring default shell...")
    zsh_path = shutil.which("zsh")
    if not zsh_path:
        print_warning("Zsh not found in PATH, cannot change default shell.")
        return ["Zsh not found in PATH"]
    desc = f"Changing shell to Zsh for user '{CURRENT_USER}'."
    cmd = ["sudo", "chsh", "-s", zsh_path, CURRENT_USER]
    return [desc] if not execute_command(cmd, desc) else []


def prompt_and_run_asus_setup() -> Tuple[List[str], List[str]]:
    """Prompts for and runs Asus-specific setup. Returns (packages, services)."""
    print_step("Asus ROG Laptop Configuration (Optional)")
    print_warning(
        "This adds a third-party repository and keys to pacman.\n"
        "Only proceed if you are on a supported Asus ROG laptop."
    )

    prompt = f"{Colors.YELLOW}{Icons.PROMPT} Do you want to run the Asus-specific setup? [y/N]: {Colors.ENDC}"
    choice = input(prompt).lower().strip()
    if choice != "y":
        print_info("Skipping Asus setup.")
        return [], []

    print_info("Proceeding with Asus setup...")
    key_id = "8F654886F17D497FEFE3DB448B15A6B0E9A3FA35"
    key_url = f"https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x{key_id}"
    key_file = "g14.sec"

    if not execute_command(
        ["sudo", "pacman-key", "--recv-keys", key_id], "Receiving g14 repo key."
    ):
        return [], []
    if not execute_command(
        ["sudo", "pacman-key", "--lsign-key", key_id], "Locally signing g14 repo key."
    ):
        return [], []

    try:
        response = requests.get(key_url, timeout=30)
        response.raise_for_status()
        with open(key_file, "wb") as f:
            f.write(response.content)
        if not execute_command(
            ["sudo", "pacman-key", "--add", key_file], "Adding key to pacman."
        ):
            return [], []
    except requests.RequestException as e:
        print_error(f"Failed to download key: {e}")
        return [], []
    finally:
        if os.path.exists(key_file):
            os.remove(key_file)

    try:
        with open("/etc/pacman.conf", "r", encoding="utf-8") as f:
            if "[g14]" not in f.read():
                repo_config = "\n[g14]\nServer = https://arch.asus-linux.org\n"
                cmd = ["sudo", "sh", "-c", f"echo '{repo_config}' >> /etc/pacman.conf"]
                if not execute_command(cmd, "Adding [g14] repo to pacman.conf."):
                    return [], []
            else:
                print_info("[g14] repository already configured.")
    except IOError as e:
        print_error(f"Could not access /etc/pacman.conf: {e}")
        return [], []

    if not execute_command(
        ["sudo", "pacman", "-Syyu"], "Synchronizing package databases."
    ):
        print_warning("Failed to sync databases. Asus packages might not be available.")

    print_success("Asus repository setup complete.")
    return (
        [
            "asusctl",
            "power-profiles-daemon",
            "supergfxctl",
            "switcheroo-control",
            "rog-control-center",
        ],
        [
            "power-profiles-daemon.service",
            "supergfxd.service",
            "switcheroo-control.service",
        ],
    )


def main() -> None:
    """Main function to run the entire setup process."""
    setup_logging()

    print(f"{Colors.BOLD}--- Arch Linux Setup Script (v5) ---{Colors.ENDC}")
    print_info(f"Logs are stored in '{LOG_FILE}'.")

    # --- Pre-flight Checks ---
    if os.geteuid() == 0:
        print_error("This script must be run as a regular user, not root.")
        sys.exit(1)
    if not shutil.which("npm"):
        print_error(
            "'npm' must be installed for this script to function. Please install it and try again."
        )
        sys.exit(1)

    # --- Sudo Credential Caching ---
    print_step("Acquiring Administrator Privileges")
    if not execute_command(
        ["sudo", "-v"], "Caching sudo credentials for the duration of the script."
    ):
        print_error("Could not acquire sudo privileges. Aborting.")
        sys.exit(1)

    # --- Ensure 'yay' is installed ---
    if not shutil.which("yay"):
        print_warning(
            "'yay' is not installed. Attempting to install it from the AUR..."
        )
        if not _install_yay():
            print_error(
                "Failed to install 'yay'. This script requires 'yay' to manage packages."
            )
            print_error("Please install it manually and run this script again.")
            sys.exit(1)
    else:
        print_success("'yay' is already installed.")

    # --- Main Workflow ---
    asus_packages, asus_services = prompt_and_run_asus_setup()

    if not run_package_installation(asus_packages):
        sys.exit(1)

    failed_configs = run_all_configurations(asus_services)

    # --- Final Summary ---
    print_step("Setup Complete!")
    if not failed_configs:
        print(
            f"{Colors.GREEN}{Colors.BOLD}{Icons.FINISH} System setup finished successfully!{Colors.ENDC}"
        )
    else:
        print(
            f"{Colors.YELLOW}{Colors.BOLD}{Icons.WARNING} System setup finished with {len(failed_configs)} error(s).{Colors.ENDC}"
        )
        print_warning("The following configuration steps failed:")
        for failure in failed_configs:
            print(f"  - {failure}")
        print_warning(f"Please review the output and check '{LOG_FILE}' for details.")

    print(
        f"\n{Colors.BLUE}{Icons.INFO} A system reboot is highly recommended to apply all changes.{Colors.ENDC}"
    )


if __name__ == "__main__":
    main()
