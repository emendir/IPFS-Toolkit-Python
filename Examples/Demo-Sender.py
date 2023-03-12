"""
This script demonstrates, together with Demo-Receiver,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run Demo-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below,
and then run this script.
"""
if True:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import ipfs_datatransmission
    import ipfs_api

# insert your peer's IPFS ID here
peer_id = ""

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peer_id)


data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode(
    "utf-8")

# sending data to peer, waiting for the transmission to complete until executing the next line of code
if ipfs_datatransmission.transmit_data(data, peer_id, "test application"):
    print("Sent Data!!")
else:
    print("Failed to send data.")
