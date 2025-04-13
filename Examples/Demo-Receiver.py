"""
This script demonstrates, together with Demo-Sender,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run this script, run Demo-Sender.py on another computer
after reading the instruct ions in that script,
and of course make sure IPFS is running on both computers first.
"""

import ipfs_datatransmission
import ipfs_api
print("IPFS ID:", ipfs_api.client.peer_id)


def on_receive(data, peer_id):
    """Eventhandler to handle received data"""
    print("Received data transmission!")
    print(data.decode("utf-8"))


# starting to listen for incoming data transmissions
listener = ipfs_datatransmission.listen_for_transmissions(
    "test_application", on_receive)
a = input("Press any key to exit...")
listener.terminate()
