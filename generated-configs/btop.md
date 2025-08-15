# Advanced btop Configuration for Gentoo Linux with Catppuccin Mocha Theme

Here's an optimized, clean configuration for `btop` with the Catppuccin Mocha color scheme, vim keybindings, and various quality-of-life improvements tailored for Gentoo Linux.

## Configuration File Location
Save this to `~/.config/btop/btop.conf`

```ini
#? Config file for btop v. 1.4.1

#* Name of a btop++/bpytop/bashtop formatted ".theme" file, "Default" and "TTY" for builtin themes.
#* Themes should be placed in "../share/btop/themes" relative to binary or "$HOME/.config/btop/themes"
color_theme = "catppuccin_mocha"

#* If the theme set background should be shown, set to False if you want terminal background transparency.
theme_background = False

#* Sets if 24-bit truecolor should be used, will convert 24-bit colors to 256 color (6x6x6 color cube) if false.
truecolor = True

#* Set to true to force tty mode regardless if a real tty has been detected or not.
#* Will force 16-color mode and TTY theme, set all graph symbols to "tty" and swap out other non tty friendly symbols.
force_tty = False

#* Define presets for the layout of the boxes. Preset 0 is always all boxes shown with default settings. Max 9 presets.
#* Format: "box_name:P:G,box_name:P:G" P=(0 or 1) for alternate positions, G=graph symbol to use for box.
#* Use whitespace " " as separator between different presets.
#* Example: "cpu:0:default,mem:0:tty,proc:1:default cpu:0:braille,proc:0:tty"
presets = "cpu:1:default,proc:0:default cpu:0:default,mem:0:default,net:0:default cpu:0:block,net:0:tty"

#* Set to True to enable "h,j,k,l,g,G" keys for directional control in lists.
#* Conflicting keys for h:"help" and k:"kill" is accessible while holding shift.
vim_keys = True

#* Rounded corners on boxes, is ignored if TTY mode is ON.
rounded_corners = True

#* Default symbols to use for graph creation, "braille", "block" or "tty".
#* "braille" offers the highest resolution but might not be included in all fonts.
#* "block" has half the resolution of braille but uses more common characters.
#* "tty" uses only 3 different symbols but will work with most fonts and should work in a real TTY.
#* Note that "tty" only has half the horizontal resolution of the other two, so will show a shorter historical view.
graph_symbol = "block"

# Graph symbol to use for graphs in cpu box, "default", "braille", "block" or "tty".
graph_symbol_cpu = "block"

# Graph symbol to use for graphs in gpu box, "default", "braille", "block" or "tty".
graph_symbol_gpu = "block"

# Graph symbol to use for graphs in cpu box, "default", "braille", "block" or "tty".
graph_symbol_mem = "block"

# Graph symbol to use for graphs in cpu box, "default", "braille", "block" or "tty".
graph_symbol_net = "block"

# Graph symbol to use for graphs in cpu box, "default", "braille", "block" or "tty".
graph_symbol_proc = "block"

#* Manually set which boxes to show. Available values are "cpu mem net proc" and "gpu0" through "gpu5", separate values with whitespace.
shown_boxes = "cpu mem net proc"

#* Update time in milliseconds, recommended 2000 ms or above for better sample times for graphs.
update_ms = 2000

#* Processes sorting, "pid" "program" "arguments" "threads" "user" "memory" "cpu lazy" "cpu direct",
#* "cpu lazy" sorts top process over time (easier to follow), "cpu direct" updates top process directly.
proc_sorting = "cpu lazy"

#* Reverse sorting order, True or False.
proc_reversed = False

#* Show processes as a tree.
proc_tree = False

#* Use the cpu graph colors in the process list.
proc_colors = True

#* Use a darkening gradient in the process list.
proc_gradient = True

#* If process cpu usage should be of the core it's running on or usage of the total available cpu power.
proc_per_core = True

#* Show process memory as bytes instead of percent.
proc_mem_bytes = True

#* Show cpu graph for each process.
proc_cpu_graphs = True

#* Use /proc/[pid]/smaps for memory information in the process info box (very slow but more accurate)
proc_info_smaps = False

#* Show proc box on left side of screen instead of right.
proc_left = False

#* (Linux) Filter processes tied to the Linux kernel(similar behavior to htop).
proc_filter_kernel = False

#* In tree-view, always accumulate child process resources in the parent process.
proc_aggregate = False

#* Sets the CPU stat shown in upper half of the CPU graph, "total" is always available.
#* Select from a list of detected attributes from the options menu.
cpu_graph_upper = "total"

#* Sets the CPU stat shown in lower half of the CPU graph, "total" is always available.
#* Select from a list of detected attributes from the options menu.
cpu_graph_lower = "total"

#* If gpu info should be shown in the cpu box. Available values = "Auto", "On" and "Off".
show_gpu_info = "Auto"

#* Toggles if the lower CPU graph should be inverted.
cpu_invert_lower = True

#* Set to True to completely disable the lower CPU graph.
cpu_single_graph = False

#* Show cpu box at bottom of screen instead of top.
cpu_bottom = False

#* Shows the system uptime in the CPU box.
show_uptime = True

#* Show cpu temperature.
check_temp = True

#* Which sensor to use for cpu temperature, use options menu to select from list of available sensors.
cpu_sensor = "Auto"

#* Show temperatures for cpu cores also if check_temp is True and sensors has been found.
show_coretemp = True

#* Set a custom mapping between core and coretemp, can be needed on certain cpus to get correct temperature for correct core.
#* Use lm-sensors or similar to see which cores are reporting temperatures on your machine.
#* Format "x:y" x=core with wrong temp, y=core with correct temp, use space as separator between multiple entries.
#* Example: "4:0 5:1 6:3"
cpu_core_map = ""

#* Which temperature scale to use, available values: "celsius", "fahrenheit", "kelvin" and "rankine".
temp_scale = "celsius"

#* Use base 10 for bits/bytes sizes, KB = 1000 instead of KiB = 1024.
base_10_sizes = False

#* Show CPU frequency.
show_cpu_freq = True

#* Draw a clock at top of screen, formatting according to strftime, empty string to disable.
#* Special formatting: /host = hostname | /user = username | /uptime = system uptime
clock_format = "%H:%M:%S"

#* Update main ui in background when menus are showing, set this to false if the menus is flickering too much for comfort.
background_update = True

#* Custom cpu model name, empty string to disable.
custom_cpu_name = ""

#* Optional filter for shown disks, should be full path of a mountpoint, separate multiple values with whitespace " ".
#* Begin line with "exclude=" to change to exclude filter, otherwise defaults to "most include" filter. Example: disks_filter="exclude=/boot /home/user".
disks_filter = ""

#* Show graphs instead of meters for memory values.
mem_graphs = True

#* Show mem box below net box instead of above.
mem_below_net = False

#* Count ZFS ARC in cached and available memory.
zfs_arc_cached = True

#* If swap memory should be shown in memory box.
show_swap = True

#* Show swap as a disk, ignores show_swap value above, inserts itself after first disk.
swap_disk = True

#* If mem box should be split to also show disks info.
show_disks = True

#* Filter out non physical disks. Set this to False to include network disks, RAM disks and similar.
only_physical = True

#* Read disks list from /etc/fstab. This also disables only_physical.
use_fstab = True

#* Setting this to True will hide all datasets, and only show ZFS pools. (IO stats will be calculated per-pool)
zfs_hide_datasets = False

#* Set to true to show available disk space for privileged users.
disk_free_priv = False

#* Toggles if io activity % (disk busy time) should be shown in regular disk usage view.
show_io_stat = True

#* Toggles io mode for disks, showing big graphs for disk read/write speeds.
io_mode = False

#* Set to True to show combined read/write io graphs in io mode.
io_graph_combined = False

#* Set the top speed for the io graphs in MiB/s (100 by default), use format "mountpoint:speed" separate disks with whitespace " ".
#* Example: "/mnt/media:100 /:20 /boot:1".
io_graph_speeds = ""

#* Set fixed values for network graphs in Mebibits. Is only used if net_auto is also set to False.
net_download = 100

net_upload = 100

#* Use network graphs auto rescaling mode, ignores any values set above and rescales down to 10 Kibibytes at the lowest.
net_auto = False

#* Sync the auto scaling for download and upload to whichever currently has the highest scale.
net_sync = True

#* Starts with the Network Interface specified here.
net_iface = ""

#* "True" shows bitrates in base 10 (Kbps, Mbps). "False" shows bitrates in binary sizes (Kibps, Mibps, etc.). "Auto" uses base_10_sizes.
base_10_bitrate = "Auto"

#* Show battery stats in top right if battery is present.
show_battery = True

#* Which battery to use if multiple are present. "Auto" for auto detection.
selected_battery = "Auto"

#* Show power stats of battery next to charge indicator.
show_battery_watts = True

#* Set loglevel for "~/.config/btop/btop.log" levels are: "ERROR" "WARNING" "INFO" "DEBUG".
#* The level set includes all lower levels, i.e. "DEBUG" will show all logging info.
log_level = "WARNING"

#* Measure PCIe throughput on NVIDIA cards, may impact performance on certain cards.
nvml_measure_pcie_speeds = True

#* Measure PCIe throughput on AMD cards, may impact performance on certain cards.
rsmi_measure_pcie_speeds = True

#* Horizontally mirror the GPU graph.
gpu_mirror_graph = True

#* Custom gpu0 model name, empty string to disable.
custom_gpu_name0 = ""

#* Custom gpu1 model name, empty string to disable.
custom_gpu_name1 = ""

#* Custom gpu2 model name, empty string to disable.
custom_gpu_name2 = ""

#* Custom gpu3 model name, empty string to disable.
custom_gpu_name3 = ""

#* Custom gpu4 model name, empty string to disable.
custom_gpu_name4 = ""

#* Custom gpu5 model name, empty string to disable.
custom_gpu_name5 = ""
```

## Catppuccin Mocha Theme File
Create this file at `~/.config/btop/themes/catppuccin_mocha.theme`:

```ini
# Catppuccin Mocha Theme for btop
# Based on https://github.com/catppuccin/catppuccin

[theme]
theme_name = "Catppuccin Mocha"
theme_description = "Soothing pastel theme for btop"

[colors]
main_fg = "#cdd6f4"
main_bg = "#1e1e2e"
title = "#cdd6f4"
hi_fg = "#f5e0dc"
selected_bg = "#585b70"
selected_fg = "#cdd6f4"
active_bg = "#313244"
active_fg = "#cdd6f4"
inactive_fg = "#6c7086"
inactive_bg = "#1e1e2e"
graph_text = "#bac2de"
meter_bg = "#313244"
proc_misc = "#b4befe"
cpu_box = "#f38ba8"
mem_box = "#a6e3a1"
net_box = "#89b4fa"
proc_box = "#f9e2af"
div_line = "#6c7086"
temp_start = "#a6e3a1"
temp_mid = "#f9e2af"
temp_end = "#f38ba8"
cpu_start = "#f5c2e7"
cpu_mid = "#cba6f7"
cpu_end = "#f38ba8"
free_start = "#a6e3a1"
free_mid = "#f9e2af"
free_end = "#f38ba8"
cached_start = "#94e2d5"
cached_mid = "#89dceb"
cached_end = "#74c7ec"
available_start = "#94e2d5"
available_mid = "#89dceb"
available_end = "#74c7ec"
used_start = "#f5c2e7"
used_mid = "#cba6f7"
used_end = "#f38ba8"
download_start = "#89b4fa"
download_mid = "#74c7ec"
download_end = "#89dceb"
upload_start = "#f5c2e7"
upload_mid = "#cba6f7"
upload_end = "#f38ba8"
process_start = "#f5c2e7"
process_mid = "#cba6f7"
process_end = "#f38ba8"
```

## Key Features

1. **Catppuccin Mocha Theme**: Soothing pastel colors that are easy on the eyes
2. **Vim Keybindings**:
   - `h/j/k/l` for navigation
   - `ESC` to enter menu
   - Quick box switching with vim keys
3. **Gentoo Optimizations**:
   - Process tree view for better portage process tracking
   - CPU frequency and temperature monitoring
   - Memory displayed in bytes (useful for monitoring compile jobs)
4. **Quality of Life Improvements**:
   - Rounded corners for aesthetic appeal
   - Truecolor support
   - Network sync for consistent scaling
   - Battery status display
   - Mouse support with wheel scrolling

## Installation on Gentoo

1. Ensure you have btop installed:
   ```bash
   sudo emerge -a sys-process/btop
   ```

2. Create the config directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/btop/themes
   ```

3. Save the configuration files as shown above.

4. (Optional) For best performance, ensure your terminal emulator supports truecolor and uses a font with good Unicode block character support (like Fira Code, JetBrains Mono, or Hack).
