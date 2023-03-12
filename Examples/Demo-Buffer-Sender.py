"""
This script demonstrates, together with Demo-Buffer-Receiver,
simple transmission of UDP buffers with the IPFS DataTransmission library.

Run Demo-Buffer-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below,
and then run this script.
"""
import time
import ipfs_datatransmission

# insert your peer's IPFS ID here
peer_id = ""


def on_buffer_received(data):
    print(data)


sender = ipfs_datatransmission.BufferSender(peer_id, "buffertest")
while True:
    time.sleep(1)
    sender.send_buffer("Hello there!".encode())
