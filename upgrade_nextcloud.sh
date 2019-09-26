#!/bin/sh
zipFile="latest.zip"
url="https://download.nextcloud.com/server/releases/$zipFile"
shaUrl="https://download.nextcloud.com/server/releases/$zipFile.sha256"
webRoot="/var/www/"
nextcloudDir="nextcloud"
oldDir="nextcloud-old"
oldBackup="nextcloud-oldbackup"
apacheUser="www-data"
apacheGroup="www-data"

apacheRunning=`pgrep -x apache2 > /dev/null`
if [ $? -eq 0 ]
then
  echo "Stopping Apache"
  systemctl stop apache2
  if [ $? -gt 0 ]
  then
    echo "Failed to stop apache"
    exit 1
  fi
fi

dbName=`grep "dbname" $webRoot$nextcloudDir/config/config.php | awk '{ print $3 }' | tr -d ',' | tr -d "'"`
dbUser=`grep "dbuser" $webRoot$nextcloudDir/config/config.php | awk '{ print $3 }' | tr -d ',' | tr -d "'"`
dbPass=`grep "dbpassword" $webRoot$nextcloudDir/config/config.php | awk '{ print $3 }' | tr -d ',' | tr -d "'"`
mysqldump -u $dbUser -p$dbPass nextcloud > "~/dumps/nextcloud.sql"
if [ $? -gt 0 ]
then
  "echo failed to backup nextcloud database"
  exit 1
fi

if [ -e $webRoot$oldBackup ]
then
  echo "Removing $webRoot$oldBackup"
  rm -r $webRoot$oldBackup
  if [ $? -gt 0 ]
  then
    echo "Failed to remove $webRoot$oldBackup"
    exit 1
  fi
fi

if [ -e $webRoot$oldDir ]
then
  echo "Renaming $webRoot$oldDir $webRoot$oldBackup"
  mv $webRoot$oldDir $webRoot$oldBackup
  if [ $? -gt 0 ]
  then
    echo "Failed to rename $webRoot$oldDir to $webRoot$oldBackup"
    exit 1
  fi
fi

if [ -e "$webRoot$zipFile" ]
then
  echo "Removing old download $webRoot$zipFile"
  rm $webRoot$zipFile
  if [ $? -gt 0 ]
  then
    echo "Failed to remove $webRoot$zipFile"
    exit 1
  fi
fi

if [ -e "$webRoot$zipFile.sha256" ]
then
  echo "Removing old checksum file $webRoot$zipFile.sha256"
  rm "$webRoot$zipFile.sha256"
  if [ $? -gt 0 ]
  then
    echo "Failed to remove $webRoot$zipFile.sha256"
    exit 1
  fi
fi

echo "Changing directory to $webRoot"
cd "$webRoot"
if [ $? -gt 0 ]
then
  echo "Failed to change directory to $webRoot"
  exit 1
fi

echo "Downloading $url"
wgetResult=`wget $url`
if [ $? -gt 0 ]
then
  echo "Failed to Download $url"
  exit 1
fi

echo "Verifying download $webRoot$zipFile"
if [ ! -e "$webRoot$zipFile" ]
then
   echo "$webRoot$zipFile does not exist"
   exit 1
fi

wgetSHA=`wget $shaUrl`
if [ ! -e "$webRoot$zipFile.sha256" ]
then
  echo "Failed to download $shaUrl"
  exit 1
fi

localSHA=`sha256sum $webRoot$zipFile | awk '{ print $1 }'`
downloadSHA=`cat $webRoot$zipFile.sha256 | awk '{ print $1 }'`

if [ $localSHA ! -eq $downloadSHA ]
then
  echo "$webRoot$zipFile integrity check failed"
  exit 1
fi

if [ -e $webRoot$nextcloudDir ]
then
  echo "Renaming $webRoot$nextcloudDir to $webRoot$oldDir"
  mv $webRoot$nextcloudDir $webRoot$oldDir
  if [ $? -gt 0 ]
  then
    echo "Failed to rename $webRoot$nextcloudDir to $webRoot$oldDir"
    exit 1
  fi
fi

echo "unzipping $webRoot$zipFile"
unzip "$webRoot$zipFile"
if [ $? -gt 0 ]
then
  echo "Failed to unzip $webRoot$zipFile"
  exit 1
fi

if [ ! -e $webRoot$nextcloudDir ]
then
  echo "$webRoot$nextcloudDir does not exist"
  exit 1
fi

if [ -e "$webRoot$oldDir/config/config.php" ]
then
  echo "Copying $webRoot$oldDir/config/config.php to $webRoot$nextcloudDir/config/config.php"
  cp -p "$webRoot$oldDir/config/config.php" "$webRoot$nextcloudDir/config/config.php"
  if [ $? -gt 0 ]
  then
    echo "failed to copy config file to $webRoot$nextcloudDir/config/config.php"
    exit 1
  fi
fi

appDirs=`diff $webRoot$oldDir/apps $webRoot$nextcloudDir/apps  | grep "^Only in $webRoot$oldDir" | awk -F': ' '{ print $2 }'`

echo "$appDirs" | while read -r line; do
    echo "Copying $webRoot$oldDir/apps/$line to $webRoot$nextcloudDir/apps/$line"
    cp -rp $webRoot$oldDir/apps/$line $webRoot$nextcloudDir/apps/$line
    if [ $? -gt 0 ]
    then
      echo "Failed to copy $webRoot$oldDir/apps/$line to $webRoot$nextcloudDir/apps/$line"
      echo "The upgrade process will need to be completed manually"
      echo "Copy any remaining apps directories to the $webRoot$nextcloudDir/apps directory"
      echo "Continue the remaining steps found at the following URL"
      echo "https://docs.nextcloud.com/server/16/admin_manual/maintenance/manual_upgrade.html"
      exit 1
    fi
done

echo "Securing $webRoot$nextcloudDir files and directories"
chown -R $apacheUser:$apacheGroup $webRoot$nextcloudDir
if [ $? -gt 0 ]
then
  echo "Failed to change the owner on $webRoot$nextcloudDir"
fi

find $webRoot$nextcloudDir -type d -exec chmod 750 {} \;
if [ $? -gt 0 ]
then
  echo "Failed to change mode on $webRoot$nextcloudDir directories"
fi

find $webRoot$nextcloudDir -type f -exec chmod 640 {} \;
if [ $? -gt 0 ]
then
  echo "Failed to change mode on $webRoot$nextcloudDir files"
fi

echo "Starting apache"
systemctl start apache2

echo "Executing nextcloud upgrade"
cd $webRoot$nextcloudDir
if [ $? -gt 0 ]
then
  echo "Failed to change directory to $webRoot$nextcloudDir"
  echo "Change directory to $webRoot$nextcloudDir and run sudo -u $apacheUser php occ upgrade"
  exit 1
fi

apacheRunning=`pgrep -x apache2 > /dev/null`
if [ $? -eq 0 ]
then
  sudo -u $apacheUser php occ upgrade
fi

echo "Nextcloud upgrade is complete!"
