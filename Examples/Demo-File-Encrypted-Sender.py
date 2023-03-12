"""
This script demonstrates, together with Demo-File-Encrypted-Receiver,
private and encrypted peer-to-peer file transmission
with the IPFS DataTransmission library.

Run Demo-File-Encrypted-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below and specify a file to upload,
and then run this script.
"""

import ipfs_datatransmission
import ipfs_api
import os
from Cryptem import Crypt

crypt = Crypt("mypassword")

# replace QmHash with your peer's IPFS ID
peer_id = ""

# insert the path of the file to transmit here
filepath = ""

# you can send any metadata your like
metadata = os.path.basename(filepath).encode()

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peer_id)


# --OPTIONAL--
def progress_update(progress):
    print(f"sending file ... {round(progress*100)}%")
# ------------


# Transmit the file. The object ft can be referenced for example to check transmission progress
ft = ipfs_datatransmission.transmit_file(
    filepath, peer_id, "my_apps_filelistener", metadata, progress_update, encryption_callbacks=(crypt.Encrypt, crypt.Decrypt))
if ft:
    print("Started Transmission")
else:
    print("Failed to start transmission")
