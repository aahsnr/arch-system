``````bash
cfdisk /dev/nvme0n1 &&
  mkfs.vfat -F 32 /dev/nvme0n1p1 &&
  cryptsetup --cipher aes-xts-plain64 --hash sha512 --use-random --verify-passphrase luksFormat /dev/nvme0n1p2 &&
  cryptsetup luksOpen /dev/nvme0n1p2 cryptlvm &&
  pvcreate /dev/mapper/cryptlvm &&
  vgcreate vg0 /dev/mapper/cryptlvm &&
  lvcreate -L 16G vg0 -n swap &&
  lvcreate -l 100%FREE vg0 -n root &&
  mkfs.btrfs -f /dev/vg0/root &&
  mkswap /dev/vg0/swap &&
  mount /dev/vg0/root /mnt &&
  swapon /dev/vg0/swap
``````


``````bash
btrfs su cr /mnt/@ &&
  btrfs su cr /mnt/@home &&
  btrfs su cr /mnt/@opt &&
  btrfs su cr /mnt/@tmp &&
  btrfs su cr /mnt/@root &&
  btrfs su cr /mnt/@srv &&
  btrfs su cr /mnt/@nix &&
  btrfs su cr /mnt/@usr@local &&
  btrfs su cr /mnt/@var &&
  btrfs su cr /mnt/@var@cache &&
  btrfs su cr /mnt/@pkg &&
  btrfs su cr /mnt/@var@crash &&
  btrfs su cr /mnt/@var@tmp &&
  btrfs su cr /mnt/@var@spool &&
  btrfs su cr /mnt/@var@log &&
  btrfs su cr /mnt/@var@log@audit &&
  btrfs su cr /mnt/@snapshots &&
  umount /mnt
``````


``````bash
mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@ /dev/vg0/root /mnt &&
  mkdir /mnt/home &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@home /dev/vg0/root /mnt/home &&
  mkdir /mnt/opt &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@opt /dev/vg0/root /mnt/opt &&
  mkdir /mnt/tmp &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@tmp /dev/vg0/root /mnt/tmp
  mkdir /mnt/root &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@root /dev/vg0/root /mnt/root &&
  mkdir /mnt/srv &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@srv /dev/vg0/root /mnt/srv &&
  mkdir /mnt/nix &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@nix /dev/vg0/root /mnt/nix &&
  mkdir -p /mnt/usr/local &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@usr@local /dev/vg0/root /mnt/usr/local &&
  mkdir /mnt/var &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var /dev/vg0/root /mnt/var &&
  mkdir /mnt/var/cache &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@cache /dev/vg0/root /mnt/var/cache &&
  mkdir -p /mnt/var/cache/pacman/pkg &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@pkg /dev/vg0/root /mnt/var/cache/pacman/pkg
  mkdir /mnt/var/crash &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@crash /dev/vg0/root /mnt/var/crash &&
  mkdir /mnt/var/tmp &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@tmp /dev/vg0/root /mnt/var/tmp &&
  mkdir /mnt/var/spool &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@spool /dev/vg0/root /mnt/var/spool &&
  mkdir /mnt/var/log &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@log /dev/vg0/root /mnt/var/log &&
  mkdir /mnt/var/log/audit &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@log@audit /dev/vg0/root /mnt/var/log/audit &&
  mkdir /mnt/.snapshots &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@snapshots /dev/vg0/root /mnt/.snapshots &&
  mkdir /mnt/boot &&
  mount /dev/nvme0n1p1 /mnt/boot
``````


``````bash
pacstrap /mnt base base-devel devtools git neovim arch-install-scripts reflector dracut yay

genfstab -U /mnt >>/mnt/etc/fstab

arch-chroot /mnt

passwd && useradd -m -G users,wheel,audio,video -s /bin/bash ahsan && passwd ahsan && EDITOR=nvim visudo

reflector --verbose -l 25 --country BD,IN --sort rate --save /etc/pacman.d/mirrorlist

ln -sf /usr/share/zoneinfo/Asia/Dhaka /etc/localtime && hwclock --systohc && nvim /etc/locale.gen && locale-gen && echo "LANG=en_US.UTF-8" >>/etc/locale.conf

passwd && useradd -m -G users,wheel,audio,video -s /bin/bash ahsan && passwd ahsan && EDITOR=nvim visudo
``````


``````bash
yay -S --noconfirm \
  arch-audit audit \
  btrfs-progs boost btrfs-progs bleachbit brightnessctl \
  chrony curl cmake chkrootkit cups cliphist celluloid \
  dosfstools dbus-python devtools deluge \
  emacs-wayland \
  fd fzf flatpak fdupes fastfetch fnm fwupd \
  grim greetd gnome-keyring gjs gtk3 gtk4 gnome-bluetooth-3.0 gobject-introspection gtk-layer-shell gtk4-layer-shell grub grub-btrfs grub-customizer \
  haveged hyprlang hyprcursor hyprwayland-scanner hypridle hyprlock hyprnome hyprdim hyprpaper hyprpicker hyprland hyprlux hyprpolkitagent \
  insync \
  jq jitterentropy-rngd \
  kitty kvantum kvantum-qt5 kvantum-theme-catppuccin-git \
  lazygit lynis libdbusmenu-gtk3 libsoup3 logrotate libva libva-nvidia-driver lsd \
  mesa mpv meson \
  networkmanager nwg-hello nodejs npm nvidia-open-dkms nvidia-utils nodejs-neovim \
  org.freedesktop.secrets \
  papirus-icon-theme python-pip python-pipx python-pynvim pipewire pipewire-alsa pipewire-pulse pipewire-jack pavucontrol pyprland python-pam power-profiles-daemon \
  qt5-wayland qt6-wayland qt5ct qt6ct \
  rng-tools rust ripgrep ranger rkhunter \
  swappy sysstat slurp swww sassc snapper snap-pac snap-pac-grub spotify-launcher starship \
  tealdeer thunderbird thunar thunar-volman thunar-media-tags-plugin thunar-archive-plugin tumbler tree-sitter-cli ttf-jetbrains-mono-nerd ttf-jetbrains-mono ttf-ubuntu-font-family typescript \
  unzip unrar upower \
  vulkan-tools vulkan-headers vulkan-validation-layers \
  wl-clipboard wf-recorder wget wireplumber \
  xorg-xwayland xournalpp xarchiver xdg-user-dirs xdg-user-dirs-gtk xdg-desktop-portal-hyprland \
  yazi \
  zathura zathura-pdf-poppler zsh zsh-completions zoxide zen-browser-avx2-bin zip
``````

### Emacs packages
``````bash
yay -S --noconfirm --needed hunspell hunspell hunspell-en_us anaconda lazydocker shellcheck shfmt graphviz 
``````

`lsblk -o name,uuid`

``````bash
nvme0n1        
├─nvme0n1p1    26FC-E891
└─nvme0n1p2    84eaf03a-2d7a-440a-aa2f-cdf63d67b3da
  └─cryptlvm   hbyaUi-q9Zv-1q0b-mI7d-0LhM-yaXB-p1tppR
    ├─vg0-swap 5a4d6d84-9b4f-448a-9522-48897cd5be33
    └─vg0-root ffedb9b8-db07-46e7-b4f1-b0ce0b9209b2
``````

``````sh
nvme0n1        
├─nvme0n1p1    15EA-4719
└─nvme0n1p2    3c70cda3-1b40-4d7a-8c8b-f80d246c7e31
  └─cryptlvm   6fKJJL-s2rM-Xh7E-I0N6-KIli-fuXO-6m9RC1
    ├─vg0-swap 7e345141-26bd-4a25-90bc-f80d6c2837f1
    └─vg0-root adfc718b-f18e-4c69-a597-39ffcd009f5c
``````

### dracut --print-cmdline gentoo
rd.driver.pre=btrfs rd.luks.uuid=luks-3c70cda3-1b40-4d7a-8c8b-f80d246c7e31 root=UUID=adfc718b-f18e-4c69-a597-39ffcd009f5c resume=UUID=7e345141-26bd-4a25-90bc-f80d6c2837f1 rd.lvm.lv=vg0/swap rd.lvm.lv=vg0/root


#### With LVM
## dracut setup
mkdir /etc/dracut.conf.d/ && nvim /etc/dracut.conf.d/dracut.conf
hostonly="yes"
compress="zstd"
add_dracutmodules+=" crypt dm rootfs-block resume lvm "
omit_dracutmodules+=" network cifs nfs nbd brltty "
force_drivers+=" btrfs "
kernel_cmdline+=" rd.luks.uuid=84eaf03a-2d7a-440a-aa2f-cdf63d67b3da root=UUID=ffedb9b8-db07-46e7-b4f1-b0ce0b9209b2 resume=UUID=5a4d6d84-9b4f-448a-9522-48897cd5be33 rd.lvm.lv=vg0/swap rd.lvm.lv=vg0/root "

#### Associated Grub
nvim /etc/default/grub
GRUB_CMDLINE_LINUX="rootfstype=btrfs quiet loglevel=0 rw rd.vconsole.keymap=us rd.luks.uuid=84eaf03a-2d7a-440a-aa2f-cdf63d67b3da root=UUID=ffedb9b8-db07-46e7-b4f1-b0ce0b9209b2 resume=UUID=5a4d6d84-9b4f-448a-9522-48897cd5be33 rd.lvm.lv=vg0/swap rd.lvm.lv=vg0/root"
GRUB_CMDLINE_LINUX_DEFAULT=""


grub-install --target=x86_64-efi --efi-directory=/boot && grub-mkconfig -o /boot/grub/grub.cfg


# dracut setup
nvim /etc/dracut.conf
compress="zstd"
hostonly="yes"
dracutmodules+=" kernel-modules rootfs-block udev-rules usrmount base fs-lib shutdown "
add_dracutmodules+=" crypt dm rootfs-block "
omit_dracutmodules+=" network cifs nfs nbd brltty "
force_drivers+=" btrfs nvidia nvidia_modeset nvidia_uvm nvidia_drm "
kernel_cmdline="quiet loglevel=3 cryptdevice=UUID=e1778643-a4b2-4cd5-b42b-25c9c995ee6b:cryptroot root=/dev/mapper/cryptroot nvidia-drm.modeset=1 rootfstype=btrfs rootflags=rw root_trim=yes"
install_items+=" /etc/crypttab "

nvim /etc/crypttab
e1778643-a4b2-4cd5-b42b-25c9c995ee6b

nvim /etc/crypttab
cryptroot UUID=e1778643-a4b2-4cd5-b42b-25c9c995ee6b none luks,initramfs

nvim /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 cryptdevice=UUID=e1778643-a4b2-4cd5-b42b-25c9c995ee6b:cryptroot root=/dev/mapper/cryptroot nvidia-drm.modeset=1 rootfstype=btrfs rootflags=rw root_trim=yes"
GRUB_CMDLINE_LINUX=""

GRUB_CMDLINE_LINUX_DEFAULT='nowatchdog nvme_load=YES rd.luks.uuid=d31114f8-58f8-4f4c-9ea2-b496daa906b7 nvidia_drm.modeset=1 loglevel=0 quiet'

pacman -S eos-dracut

reinstall-kernels

grub-install --target=x86_64-efi --efi-directory=/boot && grub-install --target=x86_64-efi --efi-directory=/boot --removable && grub-mkconfig -o /boot/grub/grub.cfg

** Systemd Setup
systemctl enable NetworkManager fstrim.timer acpid sysstat reflector reflector.timer auditd chronyd

** Secure Boot Setup

-- WARNING -- This system is for the use of authorized users only. Individuals
using this computer system without authority or in excess of their authority
are subject to having all their activities on this system monitored and
recorded by system personnel. Anyone using this system expressly consents to
such monitoring and is advised that if such monitoring reveals possible
evidence of criminal activity system personal may provide the evidence of such
monitoring to law enforcement officials.

## build toolchain
linux-api-headers- >glibc >binutils >gcc >glibc >binutils >gcc

#chroot into endeavoros
cryptsetup open --perf-no_read_workqueue --perf-no_write_workqueue --persistent /dev/nvme0n1p2 cryptroot &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@ /dev/mapper/cryptroot /mnt &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@home /dev/mapper/cryptroot /mnt/home &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@opt /dev/mapper/cryptroot /mnt/opt &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@opt /dev/mapper/cryptroot /mnt/tmp &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@root /dev/mapper/cryptroot /mnt/root &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@srv /dev/mapper/cryptroot /mnt/srv &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@nix /dev/mapper/cryptroot /mnt/nix &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@usr@local /dev/mapper/cryptroot /mnt/usr/local &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var /dev/mapper/cryptroot /mnt/var &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@cache /dev/mapper/cryptroot /mnt/var/cache &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@pkg /dev/mapper/cryptroot /mnt/var/cache/pacman/pkg &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@crash /dev/mapper/cryptroot /mnt/var/crash &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@tmp /dev/mapper/cryptroot /mnt/var/tmp &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@tmp /dev/mapper/cryptroot /mnt/var/spool &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@log /dev/mapper/cryptroot /mnt/var/log &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@var@log@audit /dev/mapper/cryptroot /mnt/var/log/audit &&
  mount -o noatime,compress=zstd:3,space_cache=v2,discard=async,subvol=@snapshots /dev/mapper/cryptroot /mnt/.snapshots &&
  mount /dev/nvme0n1p1 /mnt/boot/efi
