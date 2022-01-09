"""
This script demonstrates, together with Demo-File-Starter,
private peer-to-peer file transmission with the IPFS DataTransmission library.

Run this script, run Demo-File-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time

import IPFS_DataTransmission


# --OPTIONAL--
def ReceivingFileProgress(peer, file, filesize, progress):
    """Eventhandler which reports progress updates while receiving a file."""
    print(f"Receiving a file '{file}' from {peer}. {progress}")
# ------------


def OnDataReceived(peer, file, metadata):
    """Eventhandler which gets executed after a file has been received."""
    print("Received file.")
    print("File metadata:", metadata.decode())
    print("Filepath:", file)
    print("Sender:", peer)


file_receiver = IPFS_DataTransmission.ListenForFileTransmissions(
    "my_apps_filelistener", OnDataReceived, ReceivingFileProgress)

# endless loop to stop program from terminating
while(True):
    time.sleep(1)

# when you no longer need to listen for incoming files, clean up resources:
file_receiver.Terminate()
