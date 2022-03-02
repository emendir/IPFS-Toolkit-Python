"""
This script demonstrates, together with Demo-Conversation-Full-Receiver,
the advanced usage of the IPFS_DataTransmission.Conversation class.

Run Demo-Conversation-Full-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below,
and then run this script.
"""

import time
import IPFS_DataTransmission
import IPFS_API


# replace QmHash with your peer's IPFS ID
peerID = ""
# replace with the path of a file you would like to send
file = ""
# making sure our IPFS node finds the receiver computer on the IP layer of the internet
IPFS_API.FindPeer(peerID)


def OnMessageReceived(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conversation_name}:", message.decode(
        "utf-8"))


# Starting a conversation with name "test-con",
# where the peer is listening for conversations on a ConversationListener called "general_listener",
# waiting for the peer to join the conversation until executing the next line of code
print("Setting up conversation...")
conv = IPFS_DataTransmission.StartConversation(
    "test-con", peerID, "general_listener", OnMessageReceived)
print("Peer joined conversation.")
print("Sending file...")


def ProgressHandler(progress):
    print(f"{round(progress*100)}%")


conv.TransmitFile(file, "testfile".encode(), progress_handler=ProgressHandler)
conv.Say("Hello there!".encode('utf-8'))
print("Listening for reply...")
data = conv.Listen()
print("Peer replied: ", data)
conv.Say("Bye!".encode('utf-8'))
data = conv.Listen(timeout=5)
if data:
    print("Received data: ", data)
else:
    print("Received no more messages after waiting 5 seconds.")
conv.Close()
