"""
This script demonstrates, together with Demo-Sender,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run this script, run Demo-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time
import IPFS_DataTransmission


def OnReceive(data, PeerID):
    """Eventhandler to handle received data"""
    print("Received data transmission!")
    print(data.decode("utf-8"))


# starting to listen for incoming data transmissions
listener = IPFS_DataTransmission.ListenForTransmissions("test application", OnReceive)
# endless loop to stop program from terminating
while True:
    time.sleep(1)
