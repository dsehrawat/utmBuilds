# ==================================================================================
# Service which does a number of housekeeping operations
# 1. Software update/rollback
# 
# 
#***********************************************************************************
#* Code Copyright (C) 2021-2022 MavelTec Solutions Pvt. Ltd. All Rights Reserved.
#* Unless required by applicable law or agreed to in writing, software
#* distributed under the License is distributed on an "AS IS" BASIS,
#* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#* See LICENSE.txt for the specific language governing permissions and
#* limitations under the License.
#***********************************************************************************/

import getopt, sys
import shutil
import os 
from pathlib import Path
import platform
import time 
import configparser
import urllib
import logging

# Configuration Parameters
TARGET_BUILD_DIR = "tensileTester"
SERVICE_NAME = TARGET_BUILD_DIR + ".service"

# Parameters that we should not modify
CMD_FILE = "/tmp/__mt.cmd"
TMP_DIR = "_tmp"
LOG_FILE = '/var/log/utmService.log'
NAP_DURATION = 30   # in seconds 
BUILD_APPD_DIR = "app"

############### Function Definitions ####################
src = None
dst = None
osName = None # Name of the current operating system

filesToCopy= [
    os.path.join(BUILD_APPD_DIR,"env.yaml"),
    os.path.join(BUILD_APPD_DIR,"testgorm.db")
]

def install(buildName, src, dst, dstPath):
    destFlag = True

    # Find current operating system
    osName = platform.system()
    tmpDstDir = os.path.join(dstPath, TMP_DIR)
    
    # Check if 'zip' file exists
    logging.info("Checking if installer exists ...")
    if os.path.isfile(src) == False:
        logging.error("Source file does not exists")
        sys.exit(2)
    
    dstWithoutExtn = os.path.splitext(src)[0]
    buildNameWithoutExtn = os.path.splitext(buildName)[0]

    # Create an _tmp directory (remove if already exists)
    if os.path.exists(tmpDstDir):
        logging.info("Deleting _tmp ...")
        shutil.rmtree(tmpDstDir)
    
    # Extract the contents to _tmp directory
    logging.info("Extracting files to _tmp directory ...")
    shutil.unpack_archive(src, tmpDstDir)

    # Check if destination directory exists
    if dst == None or os.path.exists(dst) == False:
        logging.info("Destination directory does not exist")
        destFlag = False

    if destFlag:
        logging.info("Copy files from old to new ...")
        # Copy the contents
        for fileName in filesToCopy:
            destFilePath = os.path.join(tmpDstDir, buildNameWithoutExtn, fileName)
            sourceFilePath = os.path.join(dst, fileName)
            try:
                logging.info("Copy src: ", sourceFilePath)
                logging.info("Copy dst: ", destFilePath)
                shutil.copyfile(sourceFilePath, destFilePath)
            except IOError as e:
                logging.error("Error copying file: ", fileName)

    if destFlag:
        bkupFile = dst + "-bkup.zip"
        # Remove if backup already exists 
        if os.path.exists(bkupFile):
            logging.info("Deleting backup file ...")
            os.remove(bkupFile)

        # Backup current destination file
        # make_archive(dst, bkupFile)
        shutil.make_archive(dst + "-bkup", "zip", dst)
        
        # Stop the current service if running 
        if "linux" in osName.lower():
            logging.info("Stopping the service ...")
            # Stop the service
            os.system("sudo systemctl stop " + SERVICE_NAME)
            # Let the system rest for few seconds
            time.sleep(5)
            
        
        # Remove dest file now
        shutil.rmtree(dst)

    # Time to move source file to dest now
    dstDirToMove = os.path.join(dstPath, "_tmp/", buildNameWithoutExtn)
    logging.info("Directory to move: ", dstDirToMove)
    shutil.move(dstDirToMove, dst)

    # Change file permission
    os.chmod(os.path.join(dst, BUILD_APPD_DIR, TARGET_BUILD_DIR), 0o777)
    
    # Remove _tmp directory now 
    shutil.rmtree(tmpDstDir)
    os.remove(src)

    # Restart the service 
    if "linux" in osName.lower():
        logging.info("Starting the service ...")
        # Stop the service
        os.system("sudo systemctl start " + SERVICE_NAME)
        # Let the system rest for few seconds
        time.sleep(5)    

    logging.info("Installed successfully !")


def handleCommand(cmds):
    logging.info("Received commands: ", cmds)

    # Command format:
    #   [cmd]
    #   build = <utm_pi_build_v1.1.1.zip>
    #   src-path = <https://github.com/dsehrawat/utmBuilds/blob/main/bin/pi>
    #   dst-path = /home/ubuntu

    buildName = cmds['build']
    srcPath=cmds['src-path']
    dstPath = cmds['dst-path']

    if 'https' in srcPath.lower():
        # Fetch the build from Repo
        downloadCommand = "wget -O " + dstPath + "/" + buildName + " " + srcPath + "/" + buildName + "?raw=true"
        logging.info("Download command: ", downloadCommand)
        os.system(downloadCommand)
        # Verify the file
        if os.path.exists(dstPath + "/" + buildName) == True:
            logging.info("Build downloaded successfully")
    else:
        # Pick the build from local
        logging.info("Local build")

    # Build downloaded successfully...Need to install it now
    srcFile = os.path.join(dstPath,buildName)
    dstFile = dstPath + TARGET_BUILD_DIR
    install(buildName, srcFile, dstFile, dstPath)


def main():

    # Initialize logging 
    logging.basicConfig(filename=LOG_FILE, filemode='w', format='%(name)s - %(levelname)s - %(message)s')

    # Main Loop...Check for the command
    while True:
        # How will I receive a command?
        # Well, let's read a file...How about /tmp/__mt.cmd
        if os.path.isfile(CMD_FILE) == True:
            # Volla, looks like I have some command
            config = configparser.ConfigParser()
            config.read(CMD_FILE)
            if 'cmd' in config:
                # Received a command section
                commands = config['cmd']
                # Parse the command and handle it
                handleCommand(commands)

            # Remove the file
            os.remove(CMD_FILE)
            
            
        else:
            # Don't have anything to do...let's take a nap
            time.sleep(NAP_DURATION)

        
######################################################### 

if __name__ == "__main__":
    main()
