# ServerScripts
A place to keep my scripts

# lvmBackup.py
python script for Backing Up LVM logical volumes
Inspired by: https://vitobotta.com/2012/05/21/kvm-lvm-backup-cloning-and-more/

Tested on Debian 9

LVM Snapshot Backup
Creates LVM Snapshots of Logical Volumes listed in "logVols" if they are a part of volume group "volGrp"
Creates a clone of each snapshot using dd into a gz file located in "backupDir"

To Restore
```sh
gunzip backupFile.gz - | dd of=/dev/mapper/targetDevice
```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
