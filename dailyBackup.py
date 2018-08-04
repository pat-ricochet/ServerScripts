#!/usr/bin/env python3
#
# dailyBackup.py Creates backups using borg backup
# Copyright (C) 2018 Patrick O'Shea <pmoshea79@gmail.com>
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
# Tested on Debian 9 "Stretch"

import os, datetime, subprocess, time, sys
import logging
import logging.handlers
import re
import configparser
config = configparser.ConfigParser()
config.read("etc/dailyBackup.conf")

# Need to set PATH for cron
os.environ["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
mypid = os.getpid()
today = datetime.date.today()
today = today.strftime('%Y%m%d')
backupDir = "/path/to/backup/destination"
# Logging to syslog
logger = logging.getLogger('dailyBackup')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
logger.addHandler(handler)

print("dailyBackup  Copyright (C) 2018  Patrick OShea")
print("This program comes with ABSOLUTELY NO WARRANTY")
print("This is free software, and you are welcome to redistribute it")
print("under certain conditions")
print("https://www.gnu.org/licenses/gpl-3.0.en.html")
print("")

def logWriter(logMsg, retCode = None):
    logMsg = "dailyBackup["+str(mypid)+"]: "+logMsg
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
    total_size = subprocess.check_output(['du','-s', fsPath]).split()[0].decode('utf-8')
    return int(total_size)

def getBytesFree(fsPath):
    fd = os.open(fsPath, os.O_DIRECTORY)
    fsStat = os.fstatvfs(fd)
    bytesFree = fsStat.f_frsize * fsStat.f_bavail
    return bytesFree

def borgInit(backupPath):
    os.mkdir(backupPath, 0o775)
    output = subprocess.run(['borg','init','--encryption=none', backupPath], stderr=subprocess.PIPE)
    rc = output.returncode
    if rc > 0:
        logWriter("Borg init failed on repo "+backupPath, rc)

def borgCheck(backupPath, checkOption = False):
    logWriter("Checking borg repo "+backupPath)
    if checkOption:
        output = subprocess.run(['borg','check',checkOption, backupPath], stderr=subprocess.PIPE)
    else:
        output = subprocess.run(['borg','check', backupPath], stderr=subprocess.PIPE)
    rc = output.returncode
    if rc > 0:
        logWriter("Borg Check failed on repo "+backupPath, rc)

def borgPrune(backupPath, keepDays):
    output = subprocess.run(['borg','prune','--keep-daily='+keepDays, backupPath], stderr=subprocess.PIPE)
    rc = output.returncode
    if rc > 0:
        logWriter("Borg Check failed on repo "+backupPath, rc)

def createBackup(backupSource, backupDest, tag):
    output = subprocess.run(['borg','create','--compression','lz4', backupDest+"::"+tag, backupSource], stderr=subprocess.PIPE)
    rc = output.returncode
    if rc > 0:
        logWriter("Borg Create failed on repo "+backupDest+"::"+tag, rc)
    
logWriter("Daily Backup Starting")
if not os.path.isdir(backupDir):
    logWriter("Backup Directory "+backupDir+"Does Not Exist, CREATING", 1)
    os.mkdir(backupDir, 0o775)

for backupSource in config.sections():
    sourceSize = getBytesUsed(backupSource)
    destFree = getBytesFree(backupDir)
    if sourceSize >= destFree:
        logWriter("Not Enough Free Space in "+backupDir, 1)
        logWriter("Skipping Backup of "+backupSource, 1)
    else:
        backupDest = backupDir+os.path.basename(backupSource)
        if not os.path.isdir(backupDest):
            borgInit(backupDest)
        borgCheck(backupDest)
        now = datetime.datetime.now()
        tag = now.strftime('%Y%m%d_%H%M%S')
        logWriter("Backing up "+backupSource+" To "+backupDest+"::"+tag)
        createBackup(backupSource, backupDest, tag)
        borgCheck(backupDest+"::"+tag)
        if  config[backupSource]['days_to_keep']:
            keepDays = config[backupSource]['days_to_keep']
            logWriter("Pruning Backups Older Than "+keepDays+" in "+backupDest+"::"+tag)
            borgPrune(backupDest, keepDays)
