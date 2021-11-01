"""
This script demonstrates, together with Demo-File-Starter,
private peer-to-peer file transmission with the IPFS DataTransmission library.

Run this script, run Demo-File-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time
import IPFS_DataTransmission


def OnDataReceived(peer, file, metadata):
    """Eventhandler which gets executed after a file has been received."""
    print("Received file.")
    print("File metadata:", metadata.decode())
    print("Filepath:", file)
    print("Sender:", peer)


fr = IPFS_DataTransmission.ListenForFileTransmissions(
    "my_apps_filelistener", OnDataReceived)

# endless loop to stop program from terminating
while(True):
    time.sleep(1)
