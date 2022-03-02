"""
This script demonstrates, together with Demo-Buffer-Sender,
simple transmission of UDP buffers with the IPFS DataTransmission library.

Run this script, run Demo-Buffer-Sender.py on another computer
after reading the instruct ions in that script,
and of course make sure IPFS is running on both computers first.
"""
import time
import IPFS_DataTransmission


def OnBufferReceived(data):
    print(data)


listener = IPFS_DataTransmission.ListenToBuffers(OnBufferReceived, "buffertest")
while True:
    time.sleep(1)
