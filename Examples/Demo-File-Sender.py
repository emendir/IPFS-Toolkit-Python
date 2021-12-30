"""
This script demonstrates, together with Demo-File-Receiver,
private peer-to-peer file transmission with the IPFS DataTransmission library.

Run Demo-File-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below and specify a file to upload,
and then run this script.
"""

import IPFS_DataTransmission
import IPFS_API
import os

# replace QmHash with your peer's IPFS ID
peerID = "QmHash"

# insert the path of the file to transmit here
filepath = ""

# you can send any metadata your like
metadata = os.path.basename(filepath).encode()

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
IPFS_API.FindPeer(peerID)

# Transmit the file. The object ft can be referenced for example to check transmission progress
ft = IPFS_DataTransmission.TransmitFile(
    filepath, peerID, "my_apps_filelistener", metadata)
if ft:
    print("Started Transmission")
else:
    print("Failed to start transmission")
