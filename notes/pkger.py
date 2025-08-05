#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A professional, unified package utility for Arch Linux, powered by pyalpm.

This tool streamlines package management with a beautiful Tokyo Night-themed
interface. It features install, search, and remove commands, recursive AUR dependency
resolution, a dry-run mode, and an enhanced security audit that flags orphans.
"""

__author__ = "Gemini"
__version__ = "7.0.0"
__license__ = "MIT"

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set

import pyalpm
import requests

# --- Configuration & Theming ---
class Config:
    AUR_API_URL = "https://aur.archlinux.org/rpc/"

class Theme:
    BLUE, GREEN, YELLOW, RED = "\033[94m", "\033[92m", "\033[93m", "\033[91m"
    MAGENTA, CYAN, GREY, END = "\033[95m", "\033[96m", "\033[90m", "\033[0m"
    BOLD = "\033[1m"
    I_INFO, I_SUCCESS, I_WARN, I_ERROR = "⚙️", "✔️", "⚠️", "❌"
    I_SEARCH, I_PLAN, I_EXEC, I_DRY, I_TRASH = "🔍", "📝", "🚀", "✨", "🗑️"
    I_REPO, I_AUR, I_ORPHAN, I_VOTES = "📚", "👤", "👻", "⭐"

# --- User-Facing Message Functions ---
def print_info(message: str) -> None: print(f"{Theme.BLUE}{Theme.I_INFO}{Theme.END}  [INFO] {message}")
def print_success(message: str) -> None: print(f"{Theme.GREEN}{Theme.I_SUCCESS}{Theme.END}  [SUCCESS] {message}")
def print_warning(message: str) -> None: print(f"{Theme.YELLOW}{Theme.I_WARN}{Theme.END}  [WARNING] {message}")
def print_error(message: str, details: str = "") -> None:
    print(f"{Theme.RED}{Theme.I_ERROR}{Theme.END}  [ERROR] {message}", file=sys.stderr)
    if details: print(details, file=sys.stderr)

class PackageTool:
    """A class to handle package management using pyalpm and requests."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._check_system_deps()
        try:
            self.handle = pyalpm.Handle("/", "/var/lib/pacman")
            self.syncdbs = self.handle.get_syncdbs()
            self.localdb = self.handle.get_localdb()
        except pyalpm.AlpmError as e:
            raise EnvironmentError(f"Failed to initialize pyalpm: {e}") from e
        self._aur_cache: Dict[str, Dict[str, Any]] = {}

    def _check_system_deps(self) -> None:
        """Ensures required non-pacman commands are available."""
        for cmd in ["git", "sudo", "makepkg"]:
            if not shutil.which(cmd): raise EnvironmentError(f"Required command not found: '{cmd}'.")

    def _is_in_repos(self, package_name: str) -> bool:
        """Checks if a package exists in any registered sync database."""
        for db in self.syncdbs:
            if db.get_pkg(package_name): return True
        return False

    def _get_aur_info(self, package_names: List[str]) -> Dict[str, Any]:
        """Gets information for a list of AUR packages, with caching."""
        needed = [name for name in package_names if name not in self._aur_cache]
        if needed:
            params = {"v": "5", "type": "info", "arg[]": needed}
            try:
                r = requests.get(Config.AUR_API_URL, params=params, timeout=20)
                r.raise_for_status()
                for res in r.json().get("results", []): self._aur_cache[res["Name"]] = res
            except requests.RequestException as e: print_error(f"Network error: {e}")
        return {name: self._aur_cache.get(name) for name in package_names}

    def _resolve_aur_dependencies(self, aur_pkg_names: List[str]) -> List[str]:
        """Recursively resolves AUR dependencies and returns a topologically sorted list."""
        order, visited = [], set()
        dep_pattern = re.compile(r"[\w.-]+")
        def visit(pkg):
            if self.localdb.get_pkg(pkg) or pkg in order: return
            if pkg in visited: raise RuntimeError(f"Circular dependency detected: {pkg}")
            visited.add(pkg)
            info = self._get_aur_info([pkg]).get(pkg)
            if not info: raise RuntimeError(f"Could not resolve AUR dependency '{pkg}'")
            deps = info.get("depends", []) + info.get("makedepends", [])
            for dep in [match.group(0) for d in deps if (match := dep_pattern.match(d))]:
                if not self._is_in_repos(dep): visit(dep)
            order.append(pkg)
        for name in aur_pkg_names: visit(name)
        return order

    def run_search(self, search_terms: List[str]):
        """Searches official repositories and the AUR."""
        print_info(f"Searching for: '{Theme.CYAN}{' '.join(search_terms)}{Theme.END}'")
        
        print(f"\n{Theme.BLUE}{Theme.I_REPO}  Official Repositories{Theme.END}")
        repo_results_found = False
        for db in self.syncdbs:
            for pkg in db.search(" ".join(search_terms)):
                repo_results_found = True
                installed_tag = f" [{Theme.GREEN}installed{Theme.END}]" if self.localdb.get_pkg(pkg.name) else ""
                print(f"  {Theme.GREEN}{db.name}{Theme.END}/{Theme.BOLD}{pkg.name}{Theme.END} {pkg.version}{installed_tag}")
                print(f"    {pkg.desc}")
        if not repo_results_found: print("  No results found.")

        print(f"\n{Theme.MAGENTA}{Theme.I_AUR}  Arch User Repository (AUR){Theme.END}")
        try:
            r = requests.get(Config.AUR_API_URL, params={"v": "5", "type": "search", "arg": " ".join(search_terms)}, timeout=10)
            r.raise_for_status()
            aur_results = sorted(r.json().get("results", []), key=lambda x: -x['NumVotes'])
            if aur_results:
                for res in aur_results:
                    orphan_tag = f" {Theme.RED}{Theme.I_ORPHAN} ORPHANED{Theme.END}" if res.get("Maintainer") is None else ""
                    print(f"  {Theme.MAGENTA}aur{Theme.END}/{Theme.BOLD}{res['Name']}{Theme.END} {Theme.GREEN}{res['Version']}{Theme.END} [{Theme.YELLOW}{Theme.I_VOTES} {res['NumVotes']}{Theme.END}]{orphan_tag}")
                    print(f"    {res['Description']}")
            else: print("  No results found.")
        except requests.RequestException: print_warning("Could not connect to AUR for search.")

    def run_install(self, package_names: Set[str], noconfirm: bool):
        """Runs the complete installation workflow."""
        installed = {pkg.name for pkg in self.localdb.pkgcache}
        to_process = {name for name in package_names if name not in installed}
        for name in sorted(list(package_names)):
            if name in installed: print_info(f"Package '{Theme.CYAN}{name}{Theme.END}' is already installed. Skipping.")
        if not to_process:
            print_success("All requested packages are already installed or provided."); return

        repo_pkgs = sorted([p for p in to_process if self._is_in_repos(p)])
        aur_pkgs_initial = sorted([p for p in to_process if p not in repo_pkgs])
        try:
            full_aur_order = self._resolve_aur_dependencies(aur_pkgs_initial)
        except RuntimeError as e: print_error(str(e)); sys.exit(1)
        
        not_found = [p for p in aur_pkgs_initial if self._get_aur_info([p]).get(p) is None]
        if not_found: print_error("Packages not found:", "\n".join(f"  - {p}" for p in not_found)); sys.exit(1)

        print(f"\n{Theme.BLUE}{Theme.I_PLAN}  Installation plan:{Theme.END}")
        if repo_pkgs: print(f"    └── {Theme.BLUE}{Theme.I_REPO}  Repository:{Theme.END} {Theme.CYAN}{', '.join(repo_pkgs)}{Theme.END}")
        if full_aur_order: print(f"    └── {Theme.MAGENTA}{Theme.I_AUR}  AUR:{Theme.END} {Theme.CYAN}{', '.join(full_aur_order)}{Theme.END}")
        
        if self.dry_run:
            print(f"\n{Theme.MAGENTA}{Theme.I_DRY}  [DRY RUN] Would install {len(repo_pkgs)} repo and {len(full_aur_order)} AUR package(s).{Theme.END}")
            print_success("Dry run complete. No changes were made."); return

        if repo_pkgs:
            print(f"\n{Theme.BLUE}{Theme.I_EXEC}  Installing repository packages...{Theme.END}")
            cmd = ["sudo", "pacman", "-S", "--needed", "--confirm", *repo_pkgs]
            if noconfirm: cmd[4] = "--noconfirm"
            if subprocess.run(cmd).returncode != 0: print_error("Pacman failed."); sys.exit(1)

        if full_aur_order:
            with tempfile.TemporaryDirectory(prefix="aur_build_") as temp_dir_str:
                for pkg_name in full_aur_order:
                    info = self._get_aur_info([pkg_name])[pkg_name]
                    if not self._audit_and_install_aur(info, Path(temp_dir_str), noconfirm):
                        print_error(f"Halting due to failure of '{pkg_name}'."); sys.exit(1)

        print_success("All tasks completed.")

    def run_remove(self, package_names: Set[str], noconfirm: bool):
        """Runs the complete removal workflow."""
        to_remove = {name for name in package_names if self.localdb.get_pkg(name)}
        not_installed = package_names - to_remove
        for name in sorted(list(not_installed)):
            print_info(f"Package '{Theme.CYAN}{name}{Theme.END}' is not installed. Skipping.")
        if not to_remove:
            print_success("No packages to remove."); return

        print(f"\n{Theme.YELLOW}{Theme.I_WARN}  The following packages will be targeted for recursive removal:{Theme.END} {Theme.CYAN}{', '.join(sorted(list(to_remove)))}{Theme.END}")
        print_warning("This will use 'pacman -Rsc' to remove them and all their unneeded dependencies.")

        cmd = ["sudo", "pacman", "-Rsc", *sorted(list(to_remove))]
        if noconfirm: cmd.insert(3, "--noconfirm")

        if self.dry_run:
            print(f"\n{Theme.MAGENTA}{Theme.I_DRY}  [DRY RUN] Would execute command: '{' '.join(cmd)}'{Theme.END}")
            print_success("Dry run complete. No changes were made."); return
        
        print(f"\n{Theme.RED}{Theme.I_TRASH}  Executing removal command...{Theme.END}")
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            print_success("Packages removed successfully.")
        else:
            print_error("Package removal failed. Check the output from pacman above.")
        
    def _audit_and_install_aur(self, pkg_data, build_dir, noconfirm):
        pkg_name = pkg_data["Name"]
        if not noconfirm:
            orphan_tag = f" {Theme.RED}{Theme.I_ORPHAN} ORPHANED! Please be extra cautious.{Theme.END}" if pkg_data.get("Maintainer") is None else ""
            print(f"\n{Theme.YELLOW}{Theme.I_WARN}  Auditing AUR Package: {Theme.BOLD}{pkg_name}{Theme.END}{orphan_tag}")
            try:
                r = requests.get(f"https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h={pkg_name}", timeout=10)
                r.raise_for_status()
                print(f"{Theme.GREY}--- PKGBUILD Content ---\n{r.text}\n------------------------{Theme.END}")
                if input(f"Do you want to build and install '{Theme.CYAN}{pkg_name}{Theme.END}'? [y/N] ").lower() != 'y': return False
            except (requests.RequestException, EOFError, KeyboardInterrupt): return False
        else:
            print_warning(f"Skipping audit for '{pkg_name}' due to --noconfirm flag.")

        print(f"{Theme.BLUE}{Theme.I_EXEC}  Building and installing '{Theme.CYAN}{pkg_name}{Theme.END}'...{Theme.END}")
        try:
            subprocess.run(["git", "clone", f"https://aur.archlinux.org/{pkg_name}.git", build_dir/pkg_name], check=True, capture_output=True)
            cmd = ["makepkg", "-si"]
            if noconfirm: cmd.append("--noconfirm")
            proc = subprocess.run(cmd, check=True, cwd=build_dir/pkg_name, capture_output=True, text=True)
            print_success(f"Successfully installed '{pkg_name}'.")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to build '{pkg_name}'.", e.stderr); return False

def main() -> None:
    if os.geteuid() == 0: print_error("This script must not be run as root."); sys.exit(1)
    parser = argparse.ArgumentParser(description="A professional, unified package utility for Arch Linux.", epilog=f"Version: {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    install_p = subparsers.add_parser("install", help="Install or update packages.", aliases=['i'])
    install_p.add_argument("packages", nargs="+")
    install_p.add_argument("-y", "--noconfirm", action="store_true", help="Bypass all prompts.")
    install_p.add_argument("--dry-run", action="store_true", help="Preview actions without making changes.")

    search_p = subparsers.add_parser("search", help="Search for packages.", aliases=['s'])
    search_p.add_argument("terms", nargs="+")

    remove_p = subparsers.add_parser("remove", help="Remove packages and their dependencies.", aliases=['r'])
    remove_p.add_argument("packages", nargs="+")
    remove_p.add_argument("-y", "--noconfirm", action="store_true", help="Bypass pacman's confirmation prompt.")
    remove_p.add_argument("--dry-run", action="store_true", help="Preview the removal command.")

    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()
    
    try:
        tool = PackageTool(dry_run=getattr(args, 'dry_run', False))
        if args.command in ["install", "i"]: tool.run_install(set(args.packages), args.noconfirm)
        elif args.command in ["search", "s"]: tool.run_search(args.terms)
        elif args.command in ["remove", "r"]: tool.run_remove(set(args.packages), args.noconfirm)
    except EnvironmentError as e:
        print_error(str(e)); sys.exit(1)

if __name__ == "__main__":
    main()
