#!/usr/bin/env python3
"""
ArchSource Package Manager
A comprehensive package manager for Arch Linux with source building capabilities
"""

import argparse
import asyncio
import configparser
import curses
import hashlib
import json
import logging
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import aiohttp
import git
import yaml
from git import Repo

# Configuration constants
CONFIG_DIR = Path.home() / ".config" / "archsource"
CACHE_DIR = Path.home() / ".cache" / "archsource"
LOG_DIR = Path.home() / ".local" / "share" / "archsource" / "logs"
DB_PATH = CONFIG_DIR / "packages.db"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
GITHUB_REPO_URL = "https://github.com/user/archsource-configs.git"


@dataclass
class PackageInfo:
    name: str
    version: str
    description: str
    dependencies: List[str]
    source: str  # 'official' or 'aur'
    build_time: Optional[datetime] = None
    custom_makepkg_conf: Optional[str] = None


@dataclass
class BuildResult:
    package: str
    success: bool
    log_file: str
    error_msg: Optional[str] = None
    build_time: float = 0.0


class DatabaseManager:
    """Manages the local package database"""

    def __init__(self):
        self.db_path = DB_PATH
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS packages (
                name TEXT PRIMARY KEY,
                version TEXT,
                description TEXT,
                dependencies TEXT,
                source TEXT,
                build_time TEXT,
                custom_makepkg_conf TEXT,
                last_updated TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS build_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT,
                build_time TEXT,
                success BOOLEAN,
                log_file TEXT,
                error_msg TEXT,
                FOREIGN KEY(package_name) REFERENCES packages(name)
            )
        """
        )

        conn.commit()
        conn.close()

    def save_package(self, package: PackageInfo):
        """Save package information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO packages 
            (name, version, description, dependencies, source, build_time, custom_makepkg_conf, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                package.name,
                package.version,
                package.description,
                json.dumps(package.dependencies),
                package.source,
                package.build_time.isoformat() if package.build_time else None,
                package.custom_makepkg_conf,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def get_package(self, name: str) -> Optional[PackageInfo]:
        """Retrieve package information from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM packages WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PackageInfo(
            name=row[0],
            version=row[1],
            description=row[2],
            dependencies=json.loads(row[3]) if row[3] else [],
            source=row[4],
            build_time=datetime.fromisoformat(row[5]) if row[5] else None,
            custom_makepkg_conf=row[6],
        )

    def log_build(self, result: BuildResult):
        """Log build result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO build_logs (package_name, build_time, success, log_file, error_msg)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                result.package,
                datetime.now().isoformat(),
                result.success,
                result.log_file,
                result.error_msg,
            ),
        )

        conn.commit()
        conn.close()


class ConfigManager:
    """Manages configuration files and templates"""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.templates_dir = self.config_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.load_config()
        self.init_git_repo()

    def load_config(self):
        """Load main configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "github_sync": True,
                "auto_sign_keys": True,
                "parallel_builds": 4,
                "cache_size": "1GB",
                "makepkg_flags": ["-s", "-i", "--noconfirm"],
            }
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def init_git_repo(self):
        """Initialize git repository for config sync"""
        git_dir = self.config_dir / ".git"
        if not git_dir.exists() and self.config.get("github_sync"):
            try:
                self.repo = Repo.clone_from(GITHUB_REPO_URL, self.config_dir)
            except:
                self.repo = Repo.init(self.config_dir)
        elif git_dir.exists():
            self.repo = Repo(self.config_dir)
        else:
            self.repo = None

    def generate_template_makepkg_conf(self, package_name: str) -> str:
        """Generate a template makepkg.conf for a package"""
        template = f"""# Custom makepkg.conf for {package_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Compiler and linker flags
CFLAGS="-march=native -mtune=native -O2 -pipe -fno-plt -fexceptions"
CXXFLAGS="$CFLAGS -Wp,-D_FORTIFY_SOURCE=2 -Wformat -Werror=format-security"
LDFLAGS="-Wl,-O1,--sort-common,--as-needed,-z,relro,-z,now"
RUSTFLAGS="-C opt-level=2 -C target-cpu=native"

# Build environment
MAKEFLAGS="-j$(nproc)"
BUILDDIR=/tmp/makepkg

# Package options
OPTIONS=(strip docs !libtool !staticlibs emptydirs zipman purge !debug)

# Compression for final packages
COMPRESSGZ=(gzip -c -f -n)
COMPRESSBZ2=(bzip2 -c -f)
COMPRESSXZ=(xz -c -z -T 0 -)
COMPRESSLRZ=(lrzip -q)
COMPRESSLZO=(lzop -q)
COMPRESSZ=(compress -c -f)
COMPRESSLZ4=(lz4 -q)
COMPRESSLZ=(lzip -c -f)

PKGEXT='.pkg.tar.xz'
SRCEXT='.src.tar.gz'
"""

        template_path = self.templates_dir / f"{package_name}.conf"
        with open(template_path, "w") as f:
            f.write(template)

        return str(template_path)

    def get_makepkg_conf(self, package_name: str) -> Optional[str]:
        """Get custom makepkg.conf path for package"""
        conf_path = self.templates_dir / f"{package_name}.conf"
        return str(conf_path) if conf_path.exists() else None

    def sync_with_github(self):
        """Sync configuration templates with GitHub"""
        if not self.repo or not self.config.get("github_sync"):
            return

        try:
            # Pull latest changes
            origin = self.repo.remotes.origin
            origin.pull()

            # Add any new or modified files
            self.repo.git.add(A=True)

            # Commit if there are changes
            if self.repo.is_dirty():
                self.repo.index.commit(f"Auto-sync templates: {datetime.now()}")
                origin.push()

        except Exception as e:
            logging.error(f"GitHub sync failed: {e}")


class PackageDetector:
    """Detects whether a package is from official repos or AUR"""

    def __init__(self):
        self.official_repos = ["core", "extra", "community", "multilib"]

    async def detect_source(self, package_name: str) -> str:
        """Detect if package is from official repos or AUR"""
        # Check official repos first
        try:
            result = subprocess.run(
                ["pacman", "-Si", package_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return "official"
        except subprocess.TimeoutExpired:
            pass

        # Check AUR
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"https://aur.archlinux.org/rpc/?v=5&type=info&arg[]={package_name}"
                ) as response:
                    data = await response.json()
                    if data.get("resultcount", 0) > 0:
                        return "aur"
            except:
                pass

        return "unknown"


class DependencyResolver:
    """Resolves package dependencies"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.detector = PackageDetector()

    async def resolve_dependencies(self, package_name: str) -> List[str]:
        """Resolve all dependencies for a package"""
        resolved = []
        to_resolve = [package_name]
        resolved_set = set()

        while to_resolve:
            current = to_resolve.pop(0)
            if current in resolved_set:
                continue

            resolved_set.add(current)
            deps = await self.get_package_dependencies(current)

            for dep in deps:
                if dep not in resolved_set:
                    to_resolve.append(dep)

            resolved.append(current)

        return resolved[1:]  # Exclude the original package

    async def get_package_dependencies(self, package_name: str) -> List[str]:
        """Get direct dependencies for a package"""
        source = await self.detector.detect_source(package_name)

        if source == "official":
            return await self.get_official_deps(package_name)
        elif source == "aur":
            return await self.get_aur_deps(package_name)

        return []

    async def get_official_deps(self, package_name: str) -> List[str]:
        """Get dependencies from official repos"""
        try:
            result = subprocess.run(
                ["pacman", "-Si", package_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    if line.startswith("Depends On"):
                        deps_str = line.split(":", 1)[1].strip()
                        if deps_str == "None":
                            return []
                        # Parse dependencies and remove version constraints
                        deps = [
                            dep.split(">=")[0].split("=")[0].split("<")[0].strip()
                            for dep in deps_str.split()
                        ]
                        return [dep for dep in deps if dep and not dep.startswith("(")]
        except:
            pass

        return []

    async def get_aur_deps(self, package_name: str) -> List[str]:
        """Get dependencies from AUR"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"https://aur.archlinux.org/rpc/?v=5&type=info&arg[]={package_name}"
                ) as response:
                    data = await response.json()
                    if data.get("resultcount", 0) > 0:
                        pkg_info = data["results"][0]
                        deps = pkg_info.get("Depends", []) + pkg_info.get(
                            "MakeDepends", []
                        )
                        return [
                            dep.split(">=")[0].split("=")[0].split("<")[0].strip()
                            for dep in deps
                            if dep
                        ]
            except:
                pass

        return []


class KeyManager:
    """Manages GPG key signing for packages"""

    def __init__(self):
        self.signed_keys = set()

    def auto_sign_key(self, key_id: str) -> bool:
        """Automatically sign a GPG key"""
        if key_id in self.signed_keys:
            return True

        try:
            # Receive the key
            subprocess.run(
                ["gpg", "--recv-keys", key_id],
                check=True,
                capture_output=True,
                timeout=30,
            )

            # Sign the key locally
            subprocess.run(
                ["gpg", "--lsign-key", key_id],
                input="y\n",
                text=True,
                check=True,
                capture_output=True,
                timeout=30,
            )

            self.signed_keys.add(key_id)
            return True

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False


class BuildManager:
    """Manages package building operations"""

    def __init__(self, config_manager: ConfigManager, db_manager: DatabaseManager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.key_manager = KeyManager()
        self.build_queue = queue.Queue()
        self.active_builds = {}

        # Setup logging
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_file = LOG_DIR / f"builds_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

    async def build_package(self, package_name: str, source: str) -> BuildResult:
        """Build a single package"""
        start_time = datetime.now()
        log_file = (
            LOG_DIR / f"{package_name}_{start_time.strftime('%Y%m%d_%H%M%S')}.log"
        )

        try:
            if source == "official":
                result = await self.build_official_package(package_name, log_file)
            else:
                result = await self.build_aur_package(package_name, log_file)

            build_time = (datetime.now() - start_time).total_seconds()
            result.build_time = build_time

            # Log the build result
            self.db_manager.log_build(result)

            return result

        except Exception as e:
            error_result = BuildResult(
                package=package_name,
                success=False,
                log_file=str(log_file),
                error_msg=str(e),
                build_time=(datetime.now() - start_time).total_seconds(),
            )
            self.db_manager.log_build(error_result)
            return error_result

    async def build_official_package(
        self, package_name: str, log_file: Path
    ) -> BuildResult:
        """Build package from official repos using pkgctl"""
        build_dir = CACHE_DIR / "builds" / package_name
        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clone the package repository
            cmd = ["pkgctl", "repo", "clone", package_name]
            result = await self.run_command(cmd, cwd=build_dir, log_file=log_file)

            if result.returncode != 0:
                return BuildResult(
                    package=package_name,
                    success=False,
                    log_file=str(log_file),
                    error_msg="Failed to clone package repository",
                )

            pkg_dir = build_dir / package_name

            # Use custom makepkg.conf if available
            makepkg_conf = self.config_manager.get_makepkg_conf(package_name)
            env = os.environ.copy()
            if makepkg_conf:
                env["MAKEPKG_CONF"] = makepkg_conf

            # Build the package
            makepkg_flags = self.config_manager.config.get(
                "makepkg_flags", ["-s", "-i"]
            )
            cmd = ["makepkg"] + makepkg_flags
            result = await self.run_command(
                cmd, cwd=pkg_dir, log_file=log_file, env=env
            )

            success = result.returncode == 0
            return BuildResult(
                package=package_name,
                success=success,
                log_file=str(log_file),
                error_msg=None if success else "Build failed",
            )

        except Exception as e:
            return BuildResult(
                package=package_name,
                success=False,
                log_file=str(log_file),
                error_msg=str(e),
            )

    async def build_aur_package(self, package_name: str, log_file: Path) -> BuildResult:
        """Build package from AUR"""
        build_dir = CACHE_DIR / "builds" / package_name
        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clone AUR package
            aur_url = f"https://aur.archlinux.org/{package_name}.git"
            cmd = ["git", "clone", aur_url, package_name]
            result = await self.run_command(
                cmd, cwd=build_dir.parent, log_file=log_file
            )

            if result.returncode != 0:
                return BuildResult(
                    package=package_name,
                    success=False,
                    log_file=str(log_file),
                    error_msg="Failed to clone AUR package",
                )

            # Use custom makepkg.conf if available
            makepkg_conf = self.config_manager.get_makepkg_conf(package_name)
            env = os.environ.copy()
            if makepkg_conf:
                env["MAKEPKG_CONF"] = makepkg_conf

            # Build the package
            makepkg_flags = self.config_manager.config.get(
                "makepkg_flags", ["-s", "-i"]
            )
            cmd = ["makepkg"] + makepkg_flags
            result = await self.run_command(
                cmd, cwd=build_dir, log_file=log_file, env=env
            )

            success = result.returncode == 0
            return BuildResult(
                package=package_name,
                success=success,
                log_file=str(log_file),
                error_msg=None if success else "Build failed",
            )

        except Exception as e:
            return BuildResult(
                package=package_name,
                success=False,
                log_file=str(log_file),
                error_msg=str(e),
            )

    async def run_command(
        self, cmd: List[str], cwd: Path, log_file: Path, env: Optional[Dict] = None
    ) -> subprocess.CompletedProcess:
        """Run a command and log output"""
        with open(log_file, "a") as f:
            f.write(f"Running: {' '.join(cmd)}\n")
            f.write(f"Working directory: {cwd}\n")
            f.write("-" * 50 + "\n")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Stream output to log file
        with open(log_file, "a") as f:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="ignore")
                f.write(line_str)
                f.flush()

        await process.wait()
        return subprocess.CompletedProcess(cmd, process.returncode)


class NCursesUI:
    """NCurses-based user interface"""

    def __init__(self, package_manager):
        self.package_manager = package_manager
        self.current_menu = "main"
        self.selected_packages = []

    def run(self):
        """Run the ncurses interface"""
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr):
        """Main ncurses loop"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)  # Non-blocking input
        stdscr.timeout(100)  # 100ms timeout

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Draw header
            header = "ArchSource Package Manager"
            stdscr.addstr(0, (width - len(header)) // 2, header, curses.A_BOLD)
            stdscr.addstr(1, 0, "=" * width)

            if self.current_menu == "main":
                self._draw_main_menu(stdscr)
            elif self.current_menu == "search":
                self._draw_search_interface(stdscr)
            elif self.current_menu == "deps":
                self._draw_dependency_tree(stdscr)

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()
            if key == ord("q"):
                break
            elif key == ord("s"):
                self.current_menu = "search"
            elif key == ord("d"):
                self.current_menu = "deps"
            elif key == ord("m"):
                self.current_menu = "main"

    def _draw_main_menu(self, stdscr):
        """Draw the main menu"""
        menu_items = [
            "s - Search packages",
            "d - View dependency tree",
            "i - Install packages",
            "b - Build packages",
            "c - Configuration",
            "l - View logs",
            "q - Quit",
        ]

        start_y = 3
        for i, item in enumerate(menu_items):
            stdscr.addstr(start_y + i, 2, item)

    def _draw_search_interface(self, stdscr):
        """Draw search interface"""
        stdscr.addstr(3, 2, "Search packages (ESC to return):")
        stdscr.addstr(4, 2, "> ")
        # Implementation would include search functionality

    def _draw_dependency_tree(self, stdscr):
        """Draw dependency tree visualization"""
        stdscr.addstr(3, 2, "Dependency Tree (ESC to return):")
        # Implementation would show dependency visualization


class ArchSourceManager:
    """Main package manager class"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.build_manager = BuildManager(self.config_manager, self.db_manager)
        self.dependency_resolver = DependencyResolver(self.db_manager)
        self.detector = PackageDetector()
        self.ui = NCursesUI(self)

    async def install_packages(self, packages: List[str], batch: bool = False):
        """Install multiple packages"""
        all_packages = []

        for package in packages:
            # Detect source and resolve dependencies
            source = await self.detector.detect_source(package)
            deps = await self.dependency_resolver.resolve_dependencies(package)

            # Add dependencies first, then the package
            for dep in deps:
                dep_source = await self.detector.detect_source(dep)
                all_packages.append((dep, dep_source))

            all_packages.append((package, source))

        # Remove duplicates while preserving order
        seen = set()
        unique_packages = []
        for pkg, src in all_packages:
            if pkg not in seen:
                seen.add(pkg)
                unique_packages.append((pkg, src))

        # Build packages in parallel
        semaphore = asyncio.Semaphore(
            self.config_manager.config.get("parallel_builds", 4)
        )

        async def build_with_semaphore(pkg_info):
            async with semaphore:
                return await self.build_manager.build_package(pkg_info[0], pkg_info[1])

        if batch:
            # Build all at once
            tasks = [build_with_semaphore(pkg_info) for pkg_info in unique_packages]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Build sequentially for dependency order
            results = []
            for pkg_info in unique_packages:
                result = await build_with_semaphore(pkg_info)
                results.append(result)
                if not result.success:
                    print(f"Failed to build {pkg_info[0]}, stopping installation")
                    break

        return results

    def generate_template(self, package_name: str) -> str:
        """Generate makepkg.conf template for package"""
        return self.config_manager.generate_template_makepkg_conf(package_name)

    def sync_configs(self):
        """Sync configuration templates with GitHub"""
        self.config_manager.sync_with_github()

    def run_ui(self):
        """Run the ncurses interface"""
        self.ui.run()


def create_web_ui():
    """Create web UI for template management"""
    from flask import Flask, jsonify, render_template, request

    app = Flask(__name__)
    manager = ArchSourceManager()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/templates")
    def list_templates():
        templates_dir = manager.config_manager.templates_dir
        templates = []
        for conf_file in templates_dir.glob("*.conf"):
            templates.append(
                {
                    "name": conf_file.stem,
                    "path": str(conf_file),
                    "modified": conf_file.stat().st_mtime,
                }
            )
        return jsonify(templates)

    @app.route("/api/templates/<name>")
    def get_template(name):
        conf_path = manager.config_manager.templates_dir / f"{name}.conf"
        if conf_path.exists():
            with open(conf_path, "r") as f:
                return jsonify({"content": f.read()})
        return jsonify({"error": "Template not found"}), 404

    @app.route("/api/templates/<name>", methods=["POST"])
    def save_template(name):
        content = request.json.get("content", "")
        conf_path = manager.config_manager.templates_dir / f"{name}.conf"

        with open(conf_path, "w") as f:
            f.write(content)

        # Auto-sync if enabled
        if manager.config_manager.config.get("github_sync"):
            manager.sync_configs()

        return jsonify({"success": True})

    return app


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="ArchSource Package Manager")
    parser.add_argument(
        "action",
        choices=["install", "search", "template", "sync", "ui", "web"],
        help="Action to perform",
    )
    parser.add_argument("packages", nargs="*", help="Package names")
    parser.add_argument("--batch", action="store_true", help="Batch install mode")
    parser.add_argument("--web-port", type=int, default=5000, help="Web UI port")

    args = parser.parse_args()
    manager = ArchSourceManager()

    if args.action == "install":
        if not args.packages:
            print("No packages specified for installation")
            return

        results = await manager.install_packages(args.packages, args.batch)

        for result in results:
            if isinstance(result, BuildResult):
                status = "SUCCESS" if result.success else "FAILED"
                print(f"{result.package}: {status} (log: {result.log_file})")

    elif args.action == "template":
        if not args.packages:
            print("No package specified for template generation")
            return

        for package in args.packages:
            template_path = manager.generate_template(package)
            print(f"Generated template for {package}: {template_path}")

    elif args.action == "sync":
        manager.sync_configs()
        print("Configuration sync completed")

    elif args.action == "ui":
        manager.run_ui()

    elif args.action == "web":
        app = create_web_ui()
        app.run(host="0.0.0.0", port=args.web_port, debug=True)

    elif args.action == "search":
        if not args.packages:
            print("No search term specified")
            return

        # Implementation for search functionality
        for package in args.packages:
            source = await manager.detector.detect_source(package)
            print(f"{package}: {source}")


if __name__ == "__main__":
    # Ensure proper async execution
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "search", "template", "sync"]:
        asyncio.run(main())
    else:
        # For UI modes, run synchronously
        import argparse

        parser = argparse.ArgumentParser(description="ArchSource Package Manager")
        parser.add_argument(
            "action",
            nargs="?",
            default="ui",
            choices=["install", "search", "template", "sync", "ui", "web"],
            help="Action to perform",
        )
        parser.add_argument("packages", nargs="*", help="Package names")
        parser.add_argument("--batch", action="store_true", help="Batch install mode")
        parser.add_argument("--web-port", type=int, default=5000, help="Web UI port")

        args = parser.parse_args()

        if args.action == "ui":
            manager = ArchSourceManager()
            manager.run_ui()
        elif args.action == "web":
            app = create_web_ui()
            print(f"Starting web UI on http://localhost:{args.web_port}")
            app.run(host="0.0.0.0", port=args.web_port, debug=True)
        else:
            asyncio.run(main())


# Additional utility classes and functions


class CacheManager:
    """Manages package and build caching"""

    def __init__(self, cache_dir: Path, max_size: str = "1GB"):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = self._parse_size(max_size)
        self.cache_db = cache_dir / "cache.db"
        self.init_cache_db()

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '1GB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024**3
        elif size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024**2
        elif size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        else:
            return int(size_str)

    def init_cache_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                path TEXT PRIMARY KEY,
                size INTEGER,
                last_accessed TEXT,
                hash TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def add_to_cache(self, file_path: Path, category: str = "packages"):
        """Add file to cache with metadata"""
        if not file_path.exists():
            return

        cache_category_dir = self.cache_dir / category
        cache_category_dir.mkdir(exist_ok=True)

        # Calculate file hash
        file_hash = self._calculate_hash(file_path)
        file_size = file_path.stat().st_size

        # Copy to cache
        cache_path = cache_category_dir / file_path.name
        shutil.copy2(file_path, cache_path)

        # Update database
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO cache_entries (path, size, last_accessed, hash)
            VALUES (?, ?, ?, ?)
        """,
            (str(cache_path), file_size, datetime.now().isoformat(), file_hash),
        )

        conn.commit()
        conn.close()

        # Clean cache if over limit
        self._cleanup_cache()

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _cleanup_cache(self):
        """Remove old cache entries if over size limit"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT path, size FROM cache_entries ORDER BY last_accessed ASC"
        )
        entries = cursor.fetchall()

        total_size = sum(entry[1] for entry in entries)

        while total_size > self.max_size and entries:
            oldest_entry = entries.pop(0)
            cache_path = Path(oldest_entry[0])

            if cache_path.exists():
                cache_path.unlink()
                total_size -= oldest_entry[1]

            cursor.execute(
                "DELETE FROM cache_entries WHERE path = ?", (oldest_entry[0],)
            )

        conn.commit()
        conn.close()


class PacmanIntegration:
    """Integration with pacman configuration and operations"""

    def __init__(self):
        self.pacman_conf = self._parse_pacman_conf()
        self.repos = self._get_configured_repos()

    def _parse_pacman_conf(self) -> configparser.ConfigParser:
        """Parse pacman.conf file"""
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("/etc/pacman.conf")
        return config

    def _get_configured_repos(self) -> List[str]:
        """Get list of configured repositories"""
        repos = []
        for section in self.pacman_conf.sections():
            if section != "options":
                repos.append(section)
        return repos

    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is already installed"""
        try:
            result = subprocess.run(
                ["pacman", "-Qi", package_name], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def get_installed_version(self, package_name: str) -> Optional[str]:
        """Get installed version of package"""
        try:
            result = subprocess.run(
                ["pacman", "-Qi", package_name],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version"):
                        return line.split(":", 1)[1].strip()
        except subprocess.TimeoutExpired:
            pass

        return None

    def install_built_package(self, package_path: Path) -> bool:
        """Install a built package using pacman"""
        try:
            result = subprocess.run(
                ["sudo", "pacman", "-U", str(package_path), "--noconfirm"],
                capture_output=True,
                timeout=300,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False


class WebUITemplates:
    """HTML templates for the web interface"""

    INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArchSource Template Manager</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: rgba(255, 255, 255, 0.95);
            margin-top: 20px;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .template-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid #e0e0e0;
        }
        
        .template-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
        }
        
        .template-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .template-meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }
        
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            margin-right: 10px;
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .editor {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
        }
        
        .editor-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            height: 80%;
            background: white;
            border-radius: 15px;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        
        #editor-textarea {
            flex: 1;
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: none;
            outline: none;
            transition: border-color 0.3s ease;
        }
        
        #editor-textarea:focus {
            border-color: #667eea;
        }
        
        .create-form {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .status-message {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ArchSource Template Manager</h1>
            <p>Manage makepkg.conf templates for your packages</p>
        </div>
        
        <div id="status-message" class="status-message" style="display: none;"></div>
        
        <div class="create-form">
            <h3>Create New Template</h3>
            <div class="form-group">
                <label for="new-template-name">Package Name:</label>
                <input type="text" id="new-template-name" placeholder="Enter package name">
            </div>
            <button class="btn" onclick="createTemplate()">Generate Template</button>
        </div>
        
        <div id="templates-container" class="template-grid">
            <!-- Templates will be loaded here -->
        </div>
    </div>
    
    <div id="editor" class="editor">
        <div class="editor-content">
            <div class="editor-header">
                <h3 id="editor-title">Edit Template</h3>
                <div>
                    <button class="btn" onclick="saveTemplate()">Save</button>
                    <button class="btn" onclick="closeEditor()">Close</button>
                </div>
            </div>
            <textarea id="editor-textarea" placeholder="Edit your makepkg.conf template here..."></textarea>
        </div>
    </div>
    
    <script>
        let currentTemplate = null;
        
        function showStatus(message, isError = false) {
            const statusEl = document.getElementById('status-message');
            statusEl.textContent = message;
            statusEl.className = 'status-message ' + (isError ? 'status-error' : 'status-success');
            statusEl.style.display = 'block';
            
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        }
        
        async function loadTemplates() {
            try {
                const response = await fetch('/api/templates');
                const templates = await response.json();
                
                const container = document.getElementById('templates-container');
                container.innerHTML = '';
                
                templates.forEach(template => {
                    const card = document.createElement('div');
                    card.className = 'template-card';
                    
                    const modifiedDate = new Date(template.modified * 1000).toLocaleDateString();
                    
                    card.innerHTML = `
                        <div class="template-name">${template.name}</div>
                        <div class="template-meta">Modified: ${modifiedDate}</div>
                        <button class="btn" onclick="editTemplate('${template.name}')">Edit</button>
                        <button class="btn" onclick="deleteTemplate('${template.name}')">Delete</button>
                    `;
                    
                    container.appendChild(card);
                });
            } catch (error) {
                showStatus('Failed to load templates', true);
            }
        }
        
        async function createTemplate() {
            const name = document.getElementById('new-template-name').value.trim();
            if (!name) {
                showStatus('Please enter a package name', true);
                return;
            }
            
            try {
                const response = await fetch(`/api/templates/${name}/generate`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showStatus(`Template created for ${name}`);
                    document.getElementById('new-template-name').value = '';
                    loadTemplates();
                } else {
                    showStatus('Failed to create template', true);
                }
            } catch (error) {
                showStatus('Failed to create template', true);
            }
        }
        
        async function editTemplate(name) {
            try {
                const response = await fetch(`/api/templates/${name}`);
                const data = await response.json();
                
                if (data.content !== undefined) {
                    currentTemplate = name;
                    document.getElementById('editor-title').textContent = `Edit Template: ${name}`;
                    document.getElementById('editor-textarea').value = data.content;
                    document.getElementById('editor').style.display = 'block';
                } else {
                    showStatus('Failed to load template', true);
                }
            } catch (error) {
                showStatus('Failed to load template', true);
            }
        }
        
        async function saveTemplate() {
            if (!currentTemplate) return;
            
            const content = document.getElementById('editor-textarea').value;
            
            try {
                const response = await fetch(`/api/templates/${currentTemplate}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content })
                });
                
                if (response.ok) {
                    showStatus(`Template ${currentTemplate} saved successfully`);
                    closeEditor();
                    loadTemplates();
                } else {
                    showStatus('Failed to save template', true);
                }
            } catch (error) {
                showStatus('Failed to save template', true);
            }
        }
        
        function closeEditor() {
            document.getElementById('editor').style.display = 'none';
            currentTemplate = null;
        }
        
        async function deleteTemplate(name) {
            if (!confirm(`Are you sure you want to delete the template for ${name}?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/templates/${name}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    showStatus(`Template ${name} deleted`);
                    loadTemplates();
                } else {
                    showStatus('Failed to delete template', true);
                }
            } catch (error) {
                showStatus('Failed to delete template', true);
            }
        }
        
        // Load templates on page load
        document.addEventListener('DOMContentLoaded', loadTemplates);
        
        // Close editor when clicking outside
        document.getElementById('editor').addEventListener('click', function(e) {
            if (e.target === this) {
                closeEditor();
            }
        });
        
        // Handle escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && document.getElementById('editor').style.display === 'block') {
                closeEditor();
            }
        });
    </script>
</body>
</html>
    """


def create_enhanced_web_ui():
    """Create enhanced web UI with all features"""
    from flask import Flask, jsonify, render_template_string, request

    app = Flask(__name__)
    manager = ArchSourceManager()
    cache_manager = CacheManager(CACHE_DIR)

    @app.route("/")
    def index():
        return render_template_string(WebUITemplates.INDEX_TEMPLATE)

    @app.route("/api/templates")
    def list_templates():
        templates_dir = manager.config_manager.templates_dir
        templates = []
        for conf_file in templates_dir.glob("*.conf"):
            stat = conf_file.stat()
            templates.append(
                {
                    "name": conf_file.stem,
                    "path": str(conf_file),
                    "modified": stat.st_mtime,
                    "size": stat.st_size,
                }
            )
        return jsonify(sorted(templates, key=lambda x: x["modified"], reverse=True))

    @app.route("/api/templates/<name>")
    def get_template(name):
        conf_path = manager.config_manager.templates_dir / f"{name}.conf"
        if conf_path.exists():
            with open(conf_path, "r") as f:
                return jsonify({"content": f.read()})
        return jsonify({"error": "Template not found"}), 404

    @app.route("/api/templates/<name>", methods=["POST"])
    def save_template(name):
        content = request.json.get("content", "")
        conf_path = manager.config_manager.templates_dir / f"{name}.conf"

        try:
            with open(conf_path, "w") as f:
                f.write(content)

            # Auto-sync if enabled
            if manager.config_manager.config.get("github_sync"):
                manager.sync_configs()

            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/templates/<name>", methods=["DELETE"])
    def delete_template(name):
        conf_path = manager.config_manager.templates_dir / f"{name}.conf"

        try:
            if conf_path.exists():
                conf_path.unlink()

                # Auto-sync if enabled
                if manager.config_manager.config.get("github_sync"):
                    manager.sync_configs()

                return jsonify({"success": True})
            else:
                return jsonify({"error": "Template not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/templates/<name>/generate", methods=["POST"])
    def generate_template(name):
        try:
            template_path = manager.generate_template(name)
            return jsonify({"success": True, "path": template_path})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/packages/search")
    def search_packages():
        query = request.args.get("q", "")
        if not query:
            return jsonify([])

        # This would implement actual package search
        # For now, return mock data
        return jsonify(
            [
                {
                    "name": f"{query}-example",
                    "source": "official",
                    "description": "Example package",
                },
                {
                    "name": f"{query}-aur",
                    "source": "aur",
                    "description": "AUR package example",
                },
            ]
        )

    @app.route("/api/build-logs")
    def get_build_logs():
        conn = sqlite3.connect(manager.db_manager.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT package_name, build_time, success, log_file, error_msg
            FROM build_logs 
            ORDER BY build_time DESC 
            LIMIT 50
        """
        )

        logs = []
        for row in cursor.fetchall():
            logs.append(
                {
                    "package": row[0],
                    "build_time": row[1],
                    "success": bool(row[2]),
                    "log_file": row[3],
                    "error_msg": row[4],
                }
            )

        conn.close()
        return jsonify(logs)

    @app.route("/api/sync", methods=["POST"])
    def sync_configs():
        try:
            manager.sync_configs()
            return jsonify({"success": True, "message": "Sync completed"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# Installation script and setup utilities


def create_installation_script():
    """Create installation script for the package manager"""
    install_script = """#!/bin/bash
# ArchSource Package Manager Installation Script

set -e

echo "Installing ArchSource Package Manager..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root" 
   exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --user aiohttp pyyaml gitpython flask

# Create directories
mkdir -p ~/.config/archsource
mkdir -p ~/.cache/archsource
mkdir -p ~/.local/share/archsource/logs
mkdir -p ~/.local/bin

# Copy main script
cp archsource.py ~/.local/bin/archsource
chmod +x ~/.local/bin/archsource

# Create symlink for system-wide access (requires sudo)
if command -v sudo &> /dev/null; then
    echo "Creating system-wide symlink (requires sudo)..."
    sudo ln -sf ~/.local/bin/archsource /usr/local/bin/archsource
fi

# Add to PATH if not already there
if ! echo $PATH | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Added ~/.local/bin to PATH in ~/.bashrc"
    echo "Please run: source ~/.bashrc"
fi

echo "Installation completed!"
echo "Usage examples:"
echo "  archsource install package1 package2"
echo "  archsource template package_name"
echo "  archsource ui"
echo "  archsource web"
"""

    with open("install.sh", "w") as f:
        f.write(install_script)

    os.chmod("install.sh", 0o755)
    print("Created install.sh script")


if __name__ == "__main__":
    # Check if we should create installation script
    if len(sys.argv) > 1 and sys.argv[1] == "create-installer":
        create_installation_script()
        sys.exit(0)

    # Normal execution
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "search", "template", "sync"]:
        asyncio.run(main())
    else:
        # For UI modes, run synchronously
        parser = argparse.ArgumentParser(description="ArchSource Package Manager")
        parser.add_argument(
            "action",
            nargs="?",
            default="ui",
            choices=["install", "search", "template", "sync", "ui", "web"],
            help="Action to perform",
        )
        parser.add_argument("packages", nargs="*", help="Package names")
        parser.add_argument("--batch", action="store_true", help="Batch install mode")
        parser.add_argument("--web-port", type=int, default=5000, help="Web UI port")

        args = parser.parse_args()

        if args.action == "ui":
            manager = ArchSourceManager()
            manager.run_ui()
        elif args.action == "web":
            app = create_enhanced_web_ui()
            print(f"Starting web UI on http://localhost:{args.web_port}")
            app.run(host="0.0.0.0", port=args.web_port, debug=True)
        else:
            asyncio.run(main())
