"""
This script demonstrates, together with Demo-File-Encrypted-Starter,
private and encrypted peer-to-peer file transmission
with the IPFS DataTransmission library.

Run this script, run Demo-File-Encrypted-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time
import ipfs_datatransmission
from Cryptem import Crypt

crypt = Crypt("mypassword")

# --OPTIONAL--


def receiving_file_progress(peer, file, filesize, progress):
    """Eventhandler which reports progress updates while receiving a file."""
    print(f"Receiving a file '{file}' from {peer}. {progress}")
# ------------


def on_data_received(peer, file, metadata):
    """Eventhandler which gets executed after a file has been received."""
    print("Received file.")
    print("File metadata:", metadata.decode())
    print("Filepath:", file)
    print("Sender:", peer)


file_receiver = ipfs_datatransmission.listen_for_file_transmissions(
    "my_apps_filelistener", on_data_received, receiving_file_progress, encryption_callbacks=(crypt.Encrypt, crypt.Decrypt))

# endless loop to stop program from terminating
while(True):
    time.sleep(1)

# when you no longer need to listen for incoming files, clean up resources:
file_receiver.terminate()
