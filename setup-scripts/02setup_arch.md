1. First setup cachyos repository in arch linux using the following steps. The cachyos-repo will ask for user input. Make sure that there is a visible prompt for Y/n when asking for user input.
``````sh
curl https://mirror.cachyos.org/cachyos-repo.tar.xz -o cachyos-repo.tar.xz
tar xvf cachyos-repo.tar.xz && cd cachyos-repo
sudo ./cachyos-repo.sh

``````

2. Then add endeavoros repository in arch linux using the following steps:
- Add the following lines in /etc/pacman.conf after the cachyos sources but before the default arch linux sources:
``````sh
[endeavouros]
SigLevel = PackageRequired
Include = /etc/pacman.d/endeavouros-mirrorlist
``````

- Create a new file called endeavouros-mirrorlist in /etc/pacman.d/ with the following content:
``````sh
######################################################
####                                              ####
###        EndeavourOS Repository Mirrorlist       ###
####                                              ####
######################################################
#### Entry in file /etc/pacman.conf:
###     [endeavouros]
###     SigLevel = PackageRequired
###     Include = /etc/pacman.d/endeavouros-mirrorlist
######################################################
### Tip: Use the 'eos-rankimirrors' program to rank
###      these mirrors or re-order them manually.
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
``````

- Then add the following keys in arch linux using these commands
``````sh
sudo pacman-key --keyserver keyserver.ubuntu.com -r 003DB8B0CB23504F
sudo pacman-key --lsign 003DB8B0CB23504F
``````

- Then sync all the repositories with the following command:
``````sh
sudo pacman -Syyuu --noconfirm
``````
