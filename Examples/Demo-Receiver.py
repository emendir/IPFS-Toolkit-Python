"""
This script demonstrates, together with Demo-Sender,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run this script, run Demo-Sender.py on another computer
after reading the instruct ions in that script,
and of course make sure IPFS is running on both computers first.
"""

import threading
import time
if True:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import ipfs_datatransmission


def on_receive(data, peer_id):
    """Eventhandler to handle received data"""
    print("Received data transmission!")
    print(data.decode("utf-8"))


# starting to listen for incoming data transmissions
listener = ipfs_datatransmission.listen_for_transmissions("test application", on_receive)

a = input("Press any key to exit...")
listener.terminate()
