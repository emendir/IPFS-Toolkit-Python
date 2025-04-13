"""
This script demonstrates, together with Demo-Receiver,
simple, private, peer-to-peer data transmission
with the IPFS DataTransmission library.

Run Demo-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below,
and then run this script.
"""
import ipfs_datatransmission
import ipfs_api
import sys
# insert your peer's IPFS ID here
peer_id = ""

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
found_peer = ipfs_api.find_peer(peer_id)
print("Routing", found_peer)
if not found_peer:
    print("Couldn't find peer!")
    sys.exit(1)

data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode(
    "utf-8")

# sending data to peer, waiting for the transmission to complete until executing the next line of code
if ipfs_datatransmission.transmit_data(data, peer_id, "test_application"):
    print("Sent Data!!")
else:
    print("Failed to send data.")
