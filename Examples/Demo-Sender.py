"""
This script demonstrates, together with Demo-Receiver,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run Demo-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below,
and then run this script.
"""

import ipfs_datatransmission
import ipfs_api

# insert your peer's IPFS ID here
peerID = ""

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peerID)


data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode(
    "utf-8")

# sending data to peer, waiting for the transmission to complete until executing the next line of code
if ipfs_datatransmission.transmit_data(data, peerID, "test application"):
    print("Sent Data!!")
else:
    print("Failed to send data.")
