"""
This script demonstrates, together with Demo-Buffer-Receiver,
simple transmission of UDP buffers with the IPFS DataTransmission library.

Run Demo-Buffer-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below,
and then run this script.
"""
import time
import IPFS_DataTransmission

# insert your peer's IPFS ID here
peerID = ""


def OnBufferReceived(data):
    print(data)


sender = IPFS_DataTransmission.BufferSender(peerID, "buffertest")
while True:
    time.sleep(1)
    sender.SendBuffer("Hello there!".encode())
