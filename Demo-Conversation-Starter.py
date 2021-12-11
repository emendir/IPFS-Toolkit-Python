"""
This script demonstrates, together with Demo-Conversation-Receiver,
the usage of the IPFS_DataTransmission.Conversation class.

Run Demo-Conversation-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below,
and then run this script.
"""

import time
import IPFS_DataTransmission
import IPFS_API


# replace QmHash with your peer's IPFS ID
peerID = "QmHash"
peerID = "12D3KooWEkcGRPJUYyb3P2pxes6jBpET9wzDrFXxfHX8CTwHq4YB"

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
IPFS_API.FindPeer(peerID)


def OnMessageReceived(conversation, data, peerID):
    """Eventhandler for messages from the other peer."""
    print("Received message:", data.decode('utf-8'))


# Starting a conversation with name "test-con",
# where the peer is listening for conversations on a ConversationListener called "general_listener",
# waiting for the peer to join the conversation until executing the next line of code
print("Setting up conversation...")
conv = IPFS_DataTransmission.StartConversationAwait(
    "test-con", peerID, "general_listener", OnMessageReceived)
print("Peer joined conversation.")
conv.Say("Hello there!".encode('utf-8'))

# endless loop to stop program from terminating
while True:
    time.sleep(1)
