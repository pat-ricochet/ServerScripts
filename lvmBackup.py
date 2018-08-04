#!/usr/bin/env python3
#
# lvmBackup.py Creates LVM Snapshots of Logical Volumes and Clones them in gz format
# Copyright (C) 2017 Patrick O'Shea <pmoshea79@gmail.com>
# http://linkedin.com/in/patrick-oshea
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Inspired by: https://vitobotta.com/2012/05/21/kvm-lvm-backup-cloning-and-more/
# Tested on Debian 9 "Stretch"
# LVM Snapshot Backup
# Creates LVM Snapshots of Logical Volumes listed in <logVols> if they are a part of volume group <volGrp>
# Creates a clone of each snapshot using dd into a gz file located in <backupDir>
# Removes snapshots when complete
# Removes failed backups (should probably keep these somewhere else for so many days)
#
# TODO: check logical volume size and verify target has enough disk space free
# TODO: clean up logging, capture error code so logWriter can be specified fewer times

import os, datetime, subprocess, time, sys
import logging
import logging.handlers
import re

# Need to set PATH for cron
os.environ["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
mypid = os.getpid()
today = datetime.date.today()
today = today.strftime('%Y%m%d')
daysToKeep = 7
volumeGrp = "volumeGroupName"
logVols = ['logicalvolume1','logicalvolume2','logicalvolume3']
backupDir = "/path/to/backup/destination"
# Logging to syslog
logger = logging.getLogger('lvmBackup')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
logger.addHandler(handler)

print("lvmBackup  Copyright (C) 2017  Patrick OShea")
print("This program comes with ABSOLUTELY NO WARRANTY")
print("This is free software, and you are welcome to redistribute it")
print("under certain conditions")
print("https://www.gnu.org/licenses/gpl-3.0.en.html")
print("")

def logWriter(logMsg, retCode = None):
    logMsg = "lvmbackup["+str(mypid)+"]: "+logMsg
    if not retCode:
        retCode = 0
    print(logMsg)
    if retCode == 0:
        logger.info(logMsg)
    elif retCode == 1:
        logger.warn(logMsg)
    else:
        logger.error(logMsg)
    return True

def getHumanSize(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def getBytesUsed(fsPath):
    fsStat = 0
    realPath = os.path.realpath(fsPath)
    fd = os.open(realPath, os.O_RDONLY)
    try:
        fsStat = os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)
    return fsStat

def getBytesFree(fsPath):
    fd = os.open(fsPath, os.O_DIRECTORY)
    fsStat = os.fstatvfs(fd)
    bytesFree = fsStat.f_frsize * fsStat.f_bavail
    return bytesFree

def rotateBackup(logVol):
    now = time.time()
    expr = re.compile('\d{2}\d{2}\d{4}')
    for backup in os.listdir(backupDir):
        gzName = re.sub(expr, '', backup)
        if gzName == logVol+'.gz':
            fullPath = os.path.join(backupDir, backup)
            if (now - os.stat(fullPath).st_mtime) // (24 * 3600) > daysToKeep:
                if os.path.isfile(fullPath):
                    logWriter("Removing "+fullPath)
                    os.remove(fullPath)

def noErrors(lvPath, snapPath, backupFile):
    res = False
    lvExists = os.path.exists(lvPath)
    snapExists = os.path.exists(snapPath)
    backupExists = os.path.exists(backupFile)
    if not lvExists:
        logmsg = "Logical Volume "+lv+" does not exist!"
        logWriter(logmsg, 1)
    elif snapExists:
        logmsg = "Snap Shot "+snapPath+" already exists, skipping."
        logWriter(logmsg, 1)
    elif backupExists:
        logmsg = "Backup "+backupFile+" already exists, skipping."
        logWriter(logmsg, 1)
    else:
        lvBytes = getBytesUsed(lvPath)
        destBytes = getBytesFree(backupDir)
        if destBytes <= lvBytes:
            destHuman = getHumanSize(destBytes)
            lvHuman = getHumanSize(lvBytes)
            logmsg = "Backup Failed: Not enough space in destination"
            logWriter(logmsg, 1)
            logmsg = "Backup destination "+backupDir+" has "+destHuman+" remaining LV is "+lvHuman
            logWriter(logmsg, 1)
        else:
            res = True
    return res

def createSnapshot(snapFile, lvPath):
    res = False
    logmsg = "Creating snapshot "+snapFile
    logWriter(logmsg)
    snapCreate = subprocess.run(['lvcreate', '-L1G', '-s', '-n', snapFile, lvPath], stderr=subprocess.PIPE)
    if snapCreate.returncode == 0:
        res = True
    else:
        logmsg = "Snapshot "+snapPath+"creation failed"
        logWriter(logmsg, snapCreate.returncode)
        errOutput = snapCreate.stderr.decode('utf-8')
        logWriter(errOutput, snapCreate.returncode)
    return res

def removeSnapshot(snapPath):
    logmsg = 'Removing snapshot '+snapPath
    logWriter(logmsg)
    snapRemove = subprocess.run(['lvremove', '-f', snapPath], stderr=subprocess.PIPE)
    if snapRemove.returncode == 0:
        logmsg = 'Snapshot '+snapPath+' removed successfully'
        logWriter(logmsg)
    else:
        logmsg = 'Failed to remove snapshot '+snapPath
        logWriter(logmsg, snapRemove.returncode)
        errOutput = snapRemove.stderr.decode('utf-8')
        logWriter(errOutput, snapRemove.returncode)

def errorHandler(snapPath, backupFile):
    logmsg = 'Backup Failed, Removing snapshot and bad gz file'
    logWriter(logmsg, gzrc)
    backupExists = os.path.exists(backupFile)
    snapExists = os.path.exists(snapPath)
    if snapExists:
        removeSnapshot(snapPath)
    if backupExists:
        logmsg = "Removing "+backupFile
        logWriter(logmsg)
        os.remove(backupFile)

def createBackup(lv, snapFile, lvPath, backupFile):
    snapCreated = createSnapshot(snapFile, lvPath)
    if snapCreated:
        logmsg = "Creating Backup "+backupFile
        logWriter(logmsg)
        f = open(backupFile, "w")
        dd = subprocess.Popen(['dd', 'if='+snapPath, 'bs=512K'], stdout=subprocess.PIPE)
        gz = subprocess.Popen(['gzip', '-9'], stdin=dd.stdout, stdout=f)
        dd.wait()
        streamdata = gz.communicate()[0]
        f.close()
        gzrc = gz.returncode
        if gzrc == 0:
            removeSnapshot(snapPath)
            rotateBackup(lv)
        else:
            logmsg = "Backup "+backupFile+" Failed"
            logWriter(logmsg, gzrc)
            errorHandler(snapFile, backupFile)

logWriter("LVM Backups Starting")

for lv in logVols:
    vgPath = "/dev/"+volumeGrp+"/"
    lvPath = vgPath+lv
    snapFile = lv+'-snap'
    snapPath = vgPath+snapFile
    backupFile = backupDir+lv+today+'.gz'
    proceed = noErrors(lvPath, snapPath, backupFile)
    if proceed:
        createBackup(lv, snapFile, lvPath, backupFile)
