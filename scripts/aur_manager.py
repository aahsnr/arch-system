#!/usr/bin/env python3
import os
import sys
import sqlite3
import tempfile
import subprocess
import logging
import click
import json
import urllib.request
import urllib.error
import urllib.parse
import multiprocessing
import re
import concurrent.futures
from datetime import datetime, timedelta

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".config", "aur_manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DB_PATH = os.path.join(HOME, ".aur_manager.db")
USER_SYSTEMD_PATH = os.path.join(HOME, ".config", "systemd", "user")
PACMAN_HOOK_PATH = "/etc/pacman.d/hooks/aur-manager-update.hook"
AUR_RPC_URL = "https://aur.archlinux.org/rpc"
MAKEFLAGS = f"-j{multiprocessing.cpu_count()}"
CACHE_DIR = os.path.join(HOME, ".cache", "aur_manager")
LOG_FILE = os.path.join(CONFIG_DIR, "aur_manager.log")
MAX_WORKERS = multiprocessing.cpu_count() or 4

# --------------------------------------------------
# INITIAL SETUP
# --------------------------------------------------
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)

# Load config
default_config = {"auto_yes": False, "notify": True, "cache_ttl": 300}
if os.path.exists(CONFIG_FILE):
    try:
        CONFIG = json.load(open(CONFIG_FILE))
    except json.JSONDecodeError:
        CONFIG = default_config
else:
    CONFIG = default_config
    with open(CONFIG_FILE, 'w') as cf:
        json.dump(CONFIG, cf, indent=4)

# Database setup
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS aur_packages (
    name TEXT PRIMARY KEY,
    version TEXT,
    installed_date TEXT,
    last_update TEXT,
    is_git INTEGER
)
''')
conn.commit()

# --------------------------------------------------
# UTILITIES
# --------------------------------------------------
def exit_error(msg, code=1):
    logging.error(msg)
    sys.exit(code)


def cached_fetch(url):
    key = re.sub(r'[^\w]', '_', url)
    cache_file = os.path.join(CACHE_DIR, key)
    now = datetime.now().timestamp()
    ttl = CONFIG.get('cache_ttl', 300)
    if os.path.exists(cache_file) and now - os.path.getmtime(cache_file) < ttl:
        return json.load(open(cache_file))
    try:
        resp = urllib.request.urlopen(url)
        data = json.load(resp)
    except Exception as e:
        exit_error(f"Network failure fetching {url}: {e}")
    with open(cache_file, 'w') as cf:
        json.dump(data, cf)
    return data


def fetch_info(name):
    url = f"{AUR_RPC_URL}/?v=5&type=info&arg={urllib.parse.quote(name)}"
    res = cached_fetch(url)
    if res.get('resultcount', 0) > 0:
        return res['results'][0]
    exit_error(f"AUR package not found: {name}")


def run_cmd(cmd, cwd=None, prompt=None, env=None, dry=False):
    if dry:
        logging.debug(f"[dry-run] {' '.join(cmd)}")
        return
    if prompt and not click.confirm(prompt, default=CONFIG['auto_yes']):
        exit_error("Aborted by user.")
    try:
        subprocess.run(cmd, cwd=cwd, check=True, env=env)
    except Exception as e:
        exit_error(f"Command failed ({cmd}): {e}")


def shallow_clone(repo, dest, dry=False):
    run_cmd(["git", "clone", "--depth", "1", repo], cwd=dest, dry=dry)


def check_deps(pkgdir, dry=False):
    content = open(os.path.join(pkgdir, 'PKGBUILD')).read()
    match = re.search(r'depends=\(([^)]*)\)', content)
    if not match:
        return
    deps = [d.strip('"') for d in match.group(1).split()]
    missing = [d for d in deps if subprocess.run(["pacman", "-Qi", d], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0]
    if missing:
        click.echo(f"Missing deps: {', '.join(missing)}")
        if click.confirm("Install missing deps?", default=CONFIG['auto_yes']):
            run_cmd(["sudo", "pacman", "-S", "--needed"] + missing, dry=dry)
        else:
            exit_error("Cannot proceed without dependencies.")


def notify(title, message):
    if CONFIG.get('notify', True):
        subprocess.run(["notify-send", title, message])

# --------------------------------------------------
# CLI DEFINITION
# --------------------------------------------------
@click.group(invoke_without_command=True)
@click.option('-v', '--verbose', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.pass_context
def cli(ctx, verbose, dry_run):
    """AUR Manager — fast, parallel, integrated."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    ctx.obj = {'dry': dry_run}
    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())

# --------------------------------------------------
# INSTALL COMMAND
# --------------------------------------------------
@cli.command()
@click.argument('name')
@click.option('-y', '--yes', is_flag=True, help='Skip confirmations')
@click.pass_context
def install(ctx, name, yes):
    """Clone, build, and install an AUR package."""
    info = fetch_info(name)
    repo = info.get('URL') or f"https://aur.archlinux.org/{name}.git"
    with tempfile.TemporaryDirectory() as tmp:
        logging.info(f"Cloning {name}")
        shallow_clone(repo, tmp, dry=ctx.obj['dry'])
        pkgdir = os.path.join(tmp, name)
        run_cmd(["nvim", "PKGBUILD"], cwd=pkgdir,
                prompt=None if yes else "Edit PKGBUILD?", dry=ctx.obj['dry'])
        check_deps(pkgdir, dry=ctx.obj['dry'])
        env = os.environ.copy(); env['MAKEFLAGS'] = MAKEFLAGS
        cmd = ["makepkg", "-si", "--noconfirm"] if yes else ["makepkg", "-s"]
        run_cmd(cmd, cwd=pkgdir,
                prompt=None if yes else f"Build/install {name}?",
                env=env, dry=ctx.obj['dry'])
        ver = info['Version']; ig = int(name.endswith('-git'))
        now = datetime.utcnow().isoformat()
        c.execute('REPLACE INTO aur_packages VALUES (?,?,?,?,?)', (name, ver, now, now, ig))
        conn.commit(); logging.info(f"Installed {name} v{ver}")
        notify("AUR Manager", f"Installed {name} v{ver}")

# --------------------------------------------------
# REMOVE COMMAND
# --------------------------------------------------
@cli.command()
@click.argument('name')
@click.pass_context
def remove(ctx, name):
    """Uninstall via pacman and remove from tracking."""
    run_cmd(["sudo", "pacman", "-Rns", name], prompt=f"Remove {name}?", dry=ctx.obj['dry'])
    c.execute('DELETE FROM aur_packages WHERE name=?', (name,))
    conn.commit(); logging.info(f"Removed {name}")

# --------------------------------------------------
# SEARCH COMMAND
# --------------------------------------------------
@cli.command()
@click.argument('term')
@click.option('-n', '--limit', default=10, help='Max results to show')
@click.pass_context
def search(ctx, term, limit):
    """Search AUR for packages matching TERM."""
    url = f"{AUR_RPC_URL}/?v=5&type=search&arg={urllib.parse.quote(term)}"
    res = cached_fetch(url)
    results = res.get('results', [])[:limit]
    for pkg in results:
        click.echo(f"{pkg['Name']}: {pkg.get('Description','')} (votes: {pkg.get('NumVotes',0)})")
    if len(res.get('results', [])) > limit:
        click.echo(f"... and {len(res['results'])-limit} more. Use --limit to see more.")

# --------------------------------------------------
# STATUS COMMAND
# --------------------------------------------------
@cli.command()
@click.option('--all', 'show_all', is_flag=True)
@click.pass_context
def status(ctx, show_all):
    """Show packages with upstream updates."""
    c.execute('SELECT name,version FROM aur_packages')
    pkgs = c.fetchall()
    def check(pkg):
        n, v = pkg
        newv = fetch_info(n)['Version']
        return f"{n}: installed {v}, upstream {newv}" if newv != v or show_all else None
    with concurrent.futures.ThreadPoolExecutor(MAX_WORKERS) as pool:
        for out in pool.map(check, pkgs):
            if out: click.echo(out)

# --------------------------------------------------
# UPDATE COMMAND
# --------------------------------------------------
@cli.command()
@click.pass_context
def update(ctx):
    """Update outdated packages."""
    c.execute('SELECT name,last_update,is_git FROM aur_packages')
    tasks = [n for (n, lu, ig) in c.fetchall() if not (ig and datetime.utcnow() - datetime.fromisoformat(lu) < timedelta(weeks=1))]
    with concurrent.futures.ThreadPoolExecutor(MAX_WORKERS) as pool:
        pool.map(lambda name: install.callback(name, yes=CONFIG['auto_yes']), tasks)

# --------------------------------------------------
# CACHE PURGE COMMAND
# --------------------------------------------------
@cli.command()
@click.pass_context
def purge_cache(ctx):
    """Clear cached AUR metadata."""
    for f in os.listdir(CACHE_DIR):
        os.remove(os.path.join(CACHE_DIR, f))
    logging.info("Cache cleared")

# --------------------------------------------------
# SYSTEMD TIMER COMMAND
# --------------------------------------------------
@cli.command()
@click.pass_context
def enable_timer(ctx):
    """Setup systemd user timer for weekly updates."""
    os.makedirs(USER_SYSTEMD_PATH, exist_ok=True)
    svc = os.path.join(USER_SYSTEMD_PATH, 'aur-manager-update.service')
    tmr = os.path.join(USER_SYSTEMD_PATH, 'aur-manager-update.timer')
    with open(svc, 'w') as f:
        f.write(f"[Unit]\nDescription=AUR Manager Update\n\n[Service]\nType=oneshot\nExecStart={sys.executable} {os.path.realpath(__file__)} update\n")
    with open(tmr, 'w') as f:
        f.write("[Unit]\nDescription=Weekly AUR Manager Update\n\n[Timer]\nOnCalendar=weekly\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n")
    run_cmd(["systemctl", "--user", "daemon-reload"], dry=ctx.obj['dry'])
    run_cmd(["systemctl", "--user", "enable", "aur-manager-update.timer"], dry=ctx.obj['dry'])
    run_cmd(["systemctl", "--user", "start", "aur-manager-update.timer"], dry=ctx.obj['dry'])
    logging.info("Timer enabled")

# --------------------------------------------------
# PACMAN HOOK COMMAND
# --------------------------------------------------
@cli.command()
@click.pass_context
def install_hook(ctx):
    """Install pacman hook post-upgrade."""
    if os.geteuid() != 0:
        exit_error("Root required to install hook.")
    hook = (
        "[Trigger]\nOperation=Upgrade\nType=Package\nTarget=*\n\n"
        "[Action]\nDescription=AUR Manager post-upgrade\nWhen=PostTransaction\n"
        f"Exec = {sys.executable} {os.path.realpath(__file__)} update\n"
    )
    with open(PACMAN_HOOK_PATH, 'w') as f:
        f.write(hook)
    logging.info(f"Installed hook at {PACMAN_HOOK_PATH}")

if __name__ == '__main__':
    cli()
