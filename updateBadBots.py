#!/usr/bin/env python3
#
# updateBadbots.py Updates the apache badbots fail2ban filter
# makes a backup of an existing .local filter file
# and restarts fail2ban service
# Using ultimate bad bots blocker list from
# https://raw.githubusercontent.com/mitchellkrogza/apache-ultimate-bad-bot-blocker/master/_generator_lists/bad-user-agents.list
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
from bs4 import BeautifulSoup
import urllib3
import os
import subprocess
import re

http = urllib3.PoolManager()

# Need to set PATH for cron
os.environ["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

defaultFilterFile = "/etc/fail2ban/filter.d/apache-badbots.conf"
updatedFilterFile = "/etc/fail2ban/filter.d/apache-badbots.local"
ultimateBBBurl = "https://raw.githubusercontent.com/mitchellkrogza/apache-ultimate-bad-bot-blocker/master/_generator_lists/bad-user-agents.list"

response = http.request('GET', ultimateBBBurl)
ubbbFileContents = BeautifulSoup(response.data, "html.parser")

def updateBotsFile(filterFile, newBots):
    if os.path.isfile(updatedFilterFile):
        os.rename(updatedFilterFile, updatedFilterFile+".old")
    ff = open(filterFile, "r")
    lff = open(updatedFilterFile,"w")
    ffContents = ff.readlines()
    for line in ffContents:
        if line.startswith("badbotscustom"):
            line = line.replace("\n","")
            defaultBots = line.replace("badbotscustom = ","")
            line = line.replace(line, "badbotscustom = "+defaultBots+newBots+"\n")
        lff.write(line)
    ff.close()
    lff.close()

newBots = ""
for line in ubbbFileContents.get_text().split("\n"):
    line = line.replace("\\","")
    line = re.escape(line)
    if line:
        newBots = newBots+"|"+line
updateBotsFile(defaultFilterFile, newBots)

return_code = subprocess.call(['service', 'fail2ban', 'restart'])
