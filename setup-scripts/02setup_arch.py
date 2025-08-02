#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
arch_repo_setup_v4_parallel.py

A robust and idempotent Python script to automate the setup of CachyOS and
EndeavourOS repositories and enable parallel downloads in pacman.

This version features a colorful, Unicode-enhanced terminal output. It is
designed to be run multiple times, uses temporary directories, and cleans
up after itself.

USAGE:
    sudo python3 arch_repo_setup_v4_parallel.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

# --- Configuration Constants ---

ENDEAVOUROS_REPO_CONFIG = """
# --- Added by arch-repo-setup script ---
[endeavouros]
SigLevel = PackageRequired
Include = /etc/pacman.d/endeavouros-mirrorlist
# ---------------------------------------
"""

ENDEAVOUROS_MIRRORLIST_CONTENT = """
######################################################
####                                              ####
###        EndeavourOS Repository Mirrorlist       ###
####                                              ####
######################################################
## Germany
Server = https://mirror.alpix.eu/endeavouros/repo/$repo/$arch
Server = https://de.freedif.org/EndeavourOS/repo/$repo/$arch
Server = https://mirror.moson.org/endeavouros/repo/$repo/$arch
## Netherlands
Server = https://mirror.erickochen.nl/endeavouros/repo/$repo/$arch
## Sweden
Server = https://ftp.acc.umu.se/mirror/endeavouros/repo/$repo/$arch
Server = https://mirror.linux.pizza/endeavouros/repo/$repo/$arch
## Canada
Server = https://ca.gate.endeavouros.com/endeavouros/repo/$repo/$arch
## China
Server = https://mirrors.tuna.tsinghua.edu.cn/endeavouros/repo/$repo/$arch
## Vietnam
Server = https://mirror.freedif.org/EndeavourOS/repo/$repo/$arch
## Github
Server = https://raw.githubusercontent.com/endeavouros-team/repo/master/$repo/$arch
"""

PACMAN_CONF_PATH = Path("/etc/pacman.conf")
ENDEAVOUROS_MIRRORLIST_PATH = Path("/etc/pacman.d/endeavouros-mirrorlist")
PARALLEL_DOWNLOADS_COUNT = 10

# --- UI Enhancement Classes ---


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    DIM = "\033[2m"


class Symbols:
    """Unicode symbols for different message types."""

    INFO = "ℹ️ "
    SUCCESS = "✅"
    WARNING = "⚠️ "
    ERROR = "❌"
    STEP = "🚀"
    CMD = "⚙️ "
    SUB_CMD = "│  >"
    CONFIG = "🔧"


# --- UI Helper Functions ---


def print_step(message: str) -> None:
    """Prints a formatted step header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{Symbols.STEP}  {message}{Colors.RESET}")
    print(f"{Colors.BLUE}{'─' * (len(message) + 4)}{Colors.RESET}")


def print_info(message: str) -> None:
    """Prints an informational message."""
    print(f"{Colors.CYAN}{Symbols.INFO} {message}{Colors.RESET}")


def print_success(message: str) -> None:
    """Prints a success message."""
    print(f"{Colors.GREEN}{Colors.BOLD}{Symbols.SUCCESS} {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Prints a warning message."""
    print(f"{Colors.YELLOW}{Symbols.WARNING} {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Prints an error message and exits the script."""
    print(
        f"\n{Colors.RED}{Colors.BOLD}{Symbols.ERROR} ERROR: {message}{Colors.RESET}",
        file=sys.stderr,
    )
    print(f"{Colors.RED}Script aborted.{Colors.RESET}", file=sys.stderr)
    sys.exit(1)


# --- Core Logic Functions ---


def run_command(
    command: List[str], cwd: Path = None, interactive: bool = False
) -> None:
    """
    Executes a shell command and handles errors.
    If interactive is True, it allows user input by connecting to the terminal.
    Otherwise, it streams the command's output.
    """
    print(f"{Colors.DIM}{Symbols.CMD} Executing: `{' '.join(command)}`{Colors.RESET}")
    try:
        if interactive:
            # For interactive commands, connect directly to the user's terminal
            # stdin, stdout, and stderr are inherited.
            process = subprocess.Popen(command, cwd=cwd)
        else:
            # For non-interactive commands, capture and stream output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                cwd=cwd,
            )
            # Stream output in a formatted way
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    print(
                        f"{Colors.DIM}  {Symbols.SUB_CMD} {line.strip()}{Colors.RESET}"
                    )

        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

    except FileNotFoundError:
        print_error(
            f"Command not found: `{command[0]}`. Is it installed and in your PATH?"
        )
    except subprocess.CalledProcessError as e:
        print_error(
            f"Command `{' '.join(e.cmd)}` failed with exit code {e.returncode}."
        )
    except Exception as e:
        print_error(f"An unexpected error occurred while running command: {e}")


def check_privileges() -> None:
    """Exits if the script is not run as root."""
    print_step("Step 1: Checking for root privileges")
    if os.geteuid() != 0:
        print_error("This script requires root privileges. Please run with `sudo`.")
    print_success("Root privileges confirmed.")


def configure_pacman_parallel_downloads() -> None:
    """Ensures ParallelDownloads is enabled in pacman.conf."""
    print_step(f"Step 2: Configuring Pacman for Parallel Downloads")
    print_info(
        f"Ensuring 'ParallelDownloads = {PARALLEL_DOWNLOADS_COUNT}' is set in {PACMAN_CONF_PATH}"
    )

    try:
        content = PACMAN_CONF_PATH.read_text()
        new_content = None

        # Regex to find commented or uncommented ParallelDownloads line
        pattern = re.compile(r"^[#\s]*ParallelDownloads\s*=\s*\d+", re.MULTILINE)

        if pattern.search(content):
            # Line exists, so we replace it to ensure it's correct and uncommented
            target_line = f"ParallelDownloads = {PARALLEL_DOWNLOADS_COUNT}"
            new_content = pattern.sub(target_line, content)
            if new_content == content:
                print_info(
                    "ParallelDownloads setting is already correct. No changes needed."
                )
                return
        else:
            # Line doesn't exist, add it under [options]
            options_pattern = re.compile(r"^\[options\]", re.MULTILINE)
            if options_pattern.search(content):
                target_line = (
                    f"[options]\nParallelDownloads = {PARALLEL_DOWNLOADS_COUNT}"
                )
                new_content = options_pattern.sub(target_line, content)
            else:
                # If [options] section is missing, this is unusual. We'll add it.
                print_warning("[options] section not found. Adding it at the top.")
                new_content = f"[options]\nParallelDownloads = {PARALLEL_DOWNLOADS_COUNT}\n\n{content}"

        print_info(f"Backing up {PACMAN_CONF_PATH} to {PACMAN_CONF_PATH}.bak...")
        shutil.copy2(PACMAN_CONF_PATH, f"{PACMAN_CONF_PATH}.bak")

        PACMAN_CONF_PATH.write_text(new_content)
        print_success(
            f"Pacman configured with 'ParallelDownloads = {PARALLEL_DOWNLOADS_COUNT}'."
        )

    except (IOError, OSError) as e:
        print_error(f"Failed to read or write {PACMAN_CONF_PATH}: {e}")
    except re.error as e:
        print_error(f"A regex error occurred: {e}")


def setup_cachyos_repo(work_dir: Path) -> None:
    """Downloads and runs the CachyOS repository setup script."""
    print_step("Step 3: Setting up CachyOS Repository")
    tarball_url = "https://mirror.cachyos.org/cachyos-repo.tar.xz"
    tarball_path = work_dir / "cachyos-repo.tar.xz"
    repo_dir = work_dir / "cachyos-repo"
    setup_script_path = repo_dir / "cachyos-repo.sh"

    run_command(["curl", "-L", tarball_url, "-o", str(tarball_path)], cwd=work_dir)
    run_command(["tar", "xvf", str(tarball_path)], cwd=work_dir)

    if not setup_script_path.is_file():
        print_error(f"Setup script not found at expected location: {setup_script_path}")

    # The CachyOS script requires user interaction (Y/n prompt).
    print_warning(
        "The CachyOS setup script requires user input to proceed. "
        "Please follow the on-screen prompts."
    )
    # Run the script in interactive mode to allow user input.
    run_command([str(setup_script_path)], cwd=repo_dir, interactive=True)
    print_success("CachyOS repository setup script executed.")


def setup_endeavouros_repo() -> None:
    """Configures the EndeavourOS repository and GPG keys idempotently."""
    print_step("Step 4: Setting up EndeavourOS Repository")
    try:
        pacman_conf_content = PACMAN_CONF_PATH.read_text()
        if "[endeavouros]" in pacman_conf_content:
            print_info(
                "EndeavourOS repository already in /etc/pacman.conf. Skipping add."
            )
        else:
            lines = pacman_conf_content.splitlines()
            # Insert before the first official repository to give it priority
            official_repos = ["[core]", "[extra]", "[multilib]"]
            insert_pos = -1

            # Find the best position to insert the repo block
            for i, line in enumerate(lines):
                # We want to insert it before the first official repo section
                if any(repo in line for repo in official_repos):
                    insert_pos = i
                    break

            if insert_pos == -1:
                # If no standard repos are found, append to the end.
                print_warning(
                    "Could not find a standard Arch repo. Appending to end of file."
                )
                lines.append(ENDEAVOUROS_REPO_CONFIG)
            else:
                # Insert the repo config before the found official repo
                lines.insert(insert_pos, ENDEAVOUROS_REPO_CONFIG)

            print_info("Adding EndeavourOS repository to /etc/pacman.conf...")
            PACMAN_CONF_PATH.write_text("\n".join(lines))
            print_success("EndeavourOS repository added.")
    except (IOError, OSError) as e:
        print_error(f"Failed to modify {PACMAN_CONF_PATH}: {e}")

    try:
        if ENDEAVOUROS_MIRRORLIST_PATH.exists():
            print_info("EndeavourOS mirrorlist already exists. Skipping creation.")
        else:
            print_info(f"Creating mirrorlist at {ENDEAVOUROS_MIRRORLIST_PATH}...")
            ENDEAVOUROS_MIRRORLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            ENDEAVOUROS_MIRRORLIST_PATH.write_text(ENDEAVOUROS_MIRRORLIST_CONTENT)
            print_success("EndeavourOS mirrorlist created.")
    except (IOError, OSError) as e:
        print_error(f"Failed to create mirrorlist: {e}")

    print_info("Adding and signing EndeavourOS GPG keys...")
    key_id = "003DB8B0CB23504F"
    run_command(
        ["pacman-key", "--recv-keys", "--keyserver", "keyserver.ubuntu.com", key_id]
    )
    run_command(["pacman-key", "--lsign-key", key_id])
    print_success("GPG keys are present and signed.")


def sync_repositories() -> None:
    """Synchronizes all pacman repositories and updates the system."""
    print_step("Step 5: Synchronizing All Repositories")
    print_info("This may take a few moments... Parallel downloads are active!")
    run_command(["pacman", "-Syyu", "--noconfirm"])
    print_success("System repositories synchronized and packages updated.")


def main() -> None:
    """Main function to orchestrate the entire setup process."""
    try:
        check_privileges()
        configure_pacman_parallel_downloads()

        with tempfile.TemporaryDirectory(prefix="arch-setup-") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            print_info(f"Created temporary directory: {temp_dir}")

            setup_cachyos_repo(temp_dir)
            setup_endeavouros_repo()

        sync_repositories()

        print_step("Setup Complete")
        print_success("All configuration and setup tasks finished successfully.")
        print_info(
            "Your system is now configured with optimized pacman and new repositories."
        )

    except Exception as e:
        print_error(f"A critical, unexpected error occurred: {e}")
    except KeyboardInterrupt:
        print_error("\nScript execution cancelled by user.")


if __name__ == "__main__":
    main()
