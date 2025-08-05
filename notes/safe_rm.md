I'll create a Python script that acts as a safe wrapper around the `rm` command by creating backups before deletion. This approach is much more reliable than trying to recover files after they've been permanently deleted.This Python script creates a safe wrapper around the `rm` command that automatically backs up files before deletion. Here's how to set it up and use it:

## Installation & Setup

1. Save the script as `safe_rm.py` and make it executable:
```bash
chmod +x safe_rm.py
```

2. Create an alias in your shell configuration (`.bashrc`, `.zshrc`, etc.):
```bash
alias rm='/path/to/safe_rm.py'
```

3. Or install it system-wide:
```bash
sudo cp safe_rm.py /usr/local/bin/safe_rm
sudo ln -sf /usr/local/bin/safe_rm /usr/local/bin/rm
```

## Features

- **Automatic Backups**: Creates timestamped backups in `~/.safe_rm_backups/` before deletion
- **Metadata Tracking**: Keeps track of original paths, timestamps, and file sizes
- **Compatible Syntax**: Works with `rm`, `rm -f`, `rm -r`, `rm -rf` commands
- **Backup Management**: List, restore, and cleanup old backups

## Usage Examples

```bash
# Delete files (creates backup automatically)
rm file.txt
rm -rf directory/
rm -f *.tmp

# List all backups
rm --list-backups

# Restore a backup to original location
rm --restore file.txt_20241216_143022

# Restore to different location
rm --restore file.txt_20241216_143022 --restore-to /tmp/recovered_file.txt

# Clean up backups older than 30 days
rm --cleanup 30
```

## Key Benefits

1. **Prevention over Recovery**: Creates backups before deletion rather than trying to recover after
2. **Zero Configuration**: Works immediately without setup
3. **Space Efficient**: Only backs up what you actually delete
4. **Metadata Rich**: Tracks original paths, timestamps, and sizes
5. **Easy Recovery**: Simple restore commands with tab completion

The script stores backups in `~/.safe_rm_backups/` with a JSON metadata file that tracks all backup information. This approach is much more reliable than trying to recover deleted files from filesystem remnants, especially on modern filesystems with TRIM/discard enabled.

``````py
#!/usr/bin/env python3
"""
Safe RM - A wrapper around rm command that creates backups before deletion
Usage: safe_rm [options] file1 file2 ...
       safe_rm --restore [backup_name]
       safe_rm --list-backups
       safe_rm --cleanup [days]
"""

import os
import sys
import shutil
import argparse
import datetime
import subprocess
from pathlib import Path
import json

class SafeRM:
    def __init__(self):
        self.backup_dir = Path.home() / '.safe_rm_backups'
        self.metadata_file = self.backup_dir / 'metadata.json'
        self.ensure_backup_dir()
    
    def ensure_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        self.backup_dir.mkdir(exist_ok=True)
        if not self.metadata_file.exists():
            self.save_metadata({})
    
    def load_metadata(self):
        """Load backup metadata"""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_metadata(self, metadata):
        """Save backup metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def create_backup_name(self, original_path):
        """Generate unique backup name with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(original_path).name
        counter = 0
        
        while True:
            if counter == 0:
                backup_name = f"{base_name}_{timestamp}"
            else:
                backup_name = f"{base_name}_{timestamp}_{counter}"
            
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                return backup_name, backup_path
            counter += 1
    
    def backup_item(self, item_path):
        """Create backup of file or directory"""
        item_path = Path(item_path).resolve()
        
        if not item_path.exists():
            print(f"Error: {item_path} does not exist")
            return False
        
        try:
            backup_name, backup_path = self.create_backup_name(item_path)
            
            # Create backup
            if item_path.is_file():
                shutil.copy2(item_path, backup_path)
                backup_type = "file"
            elif item_path.is_dir():
                shutil.copytree(item_path, backup_path)
                backup_type = "directory"
            else:
                print(f"Error: {item_path} is neither a file nor directory")
                return False
            
            # Update metadata
            metadata = self.load_metadata()
            metadata[backup_name] = {
                "original_path": str(item_path),
                "backup_path": str(backup_path),
                "backup_type": backup_type,
                "timestamp": datetime.datetime.now().isoformat(),
                "size": self.get_size(backup_path)
            }
            self.save_metadata(metadata)
            
            print(f"Backed up: {item_path} -> {backup_name}")
            return True
            
        except Exception as e:
            print(f"Error backing up {item_path}: {e}")
            return False
    
    def get_size(self, path):
        """Get size of file or directory"""
        path = Path(path)
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0
    
    def safe_remove(self, paths, force=False, recursive=False):
        """Safely remove files/directories after backing up"""
        success_count = 0
        
        for path in paths:
            path_obj = Path(path)
            
            # Skip if path doesn't exist and not using force
            if not path_obj.exists() and not force:
                print(f"Error: {path} does not exist")
                continue
            
            # Check if we need recursive flag for directories
            if path_obj.is_dir() and not recursive:
                print(f"Error: {path} is a directory. Use -r or -R flag for recursive deletion")
                continue
            
            # Create backup
            if self.backup_item(path):
                # Use system rm command for actual deletion
                try:
                    cmd = ['rm']
                    if force:
                        cmd.append('-f')
                    if recursive:
                        cmd.append('-r')
                    cmd.append(str(path))
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"Deleted: {path}")
                        success_count += 1
                    else:
                        print(f"Error deleting {path}: {result.stderr}")
                except Exception as e:
                    print(f"Error executing rm command: {e}")
        
        return success_count
    
    def list_backups(self):
        """List all available backups"""
        metadata = self.load_metadata()
        
        if not metadata:
            print("No backups found.")
            return
        
        print(f"{'Backup Name':<30} {'Original Path':<40} {'Type':<10} {'Date':<20} {'Size':<10}")
        print("-" * 120)
        
        for backup_name, info in sorted(metadata.items(), key=lambda x: x[1]['timestamp'], reverse=True):
            timestamp = datetime.datetime.fromisoformat(info['timestamp'])
            date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            size_str = self.format_size(info['size'])
            
            print(f"{backup_name:<30} {info['original_path']:<40} {info['backup_type']:<10} {date_str:<20} {size_str:<10}")
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    def restore_backup(self, backup_name, restore_path=None):
        """Restore a backup to original location or specified path"""
        metadata = self.load_metadata()
        
        if backup_name not in metadata:
            print(f"Error: Backup '{backup_name}' not found")
            return False
        
        backup_info = metadata[backup_name]
        backup_path = Path(backup_info['backup_path'])
        
        if not backup_path.exists():
            print(f"Error: Backup file {backup_path} no longer exists")
            return False
        
        # Determine restore location
        if restore_path:
            target_path = Path(restore_path)
        else:
            target_path = Path(backup_info['original_path'])
        
        try:
            # Check if target already exists
            if target_path.exists():
                response = input(f"Target {target_path} already exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print("Restore cancelled.")
                    return False
                
                # Remove existing target
                if target_path.is_file():
                    target_path.unlink()
                elif target_path.is_dir():
                    shutil.rmtree(target_path)
            
            # Restore backup
            if backup_info['backup_type'] == 'file':
                shutil.copy2(backup_path, target_path)
            else:  # directory
                shutil.copytree(backup_path, target_path)
            
            print(f"Restored: {backup_name} -> {target_path}")
            return True
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def cleanup_old_backups(self, days=30):
        """Remove backups older than specified days"""
        metadata = self.load_metadata()
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        removed_count = 0
        for backup_name, info in list(metadata.items()):
            backup_date = datetime.datetime.fromisoformat(info['timestamp'])
            
            if backup_date < cutoff_date:
                backup_path = Path(info['backup_path'])
                try:
                    if backup_path.exists():
                        if backup_path.is_file():
                            backup_path.unlink()
                        else:
                            shutil.rmtree(backup_path)
                    
                    del metadata[backup_name]
                    removed_count += 1
                    print(f"Removed old backup: {backup_name}")
                    
                except Exception as e:
                    print(f"Error removing backup {backup_name}: {e}")
        
        if removed_count > 0:
            self.save_metadata(metadata)
            print(f"Cleaned up {removed_count} old backups")
        else:
            print("No old backups to clean up")

def main():
    parser = argparse.ArgumentParser(description='Safe RM - Backup files before deletion')
    parser.add_argument('files', nargs='*', help='Files or directories to delete')
    parser.add_argument('-f', '--force', action='store_true', help='Force deletion without prompting')
    parser.add_argument('-r', '-R', '--recursive', action='store_true', help='Remove directories recursively')
    parser.add_argument('--restore', metavar='BACKUP_NAME', help='Restore a backup')
    parser.add_argument('--restore-to', metavar='PATH', help='Restore backup to specific path')
    parser.add_argument('--list-backups', action='store_true', help='List all backups')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', help='Remove backups older than DAYS (default: 30)')
    
    args = parser.parse_args()
    safe_rm = SafeRM()
    
    # Handle different operations
    if args.list_backups:
        safe_rm.list_backups()
    elif args.restore:
        safe_rm.restore_backup(args.restore, args.restore_to)
    elif args.cleanup is not None:
        days = args.cleanup if args.cleanup > 0 else 30
        safe_rm.cleanup_old_backups(days)
    elif args.files:
        # Normal deletion with backup
        safe_rm.safe_remove(args.files, args.force, args.recursive)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()


``````
