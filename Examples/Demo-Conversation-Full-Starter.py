"""
This script demonstrates, together with Demo-Conversation-Full-Receiver,
the advanced usage of the ipfs_datatransmission.Conversation class.

Run Demo-Conversation-Full-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peerID variable below,
and then run this script.
"""

import ipfs_datatransmission
import ipfs_api


# insert your peer's IPFS ID here
peerID = ""
# replace with the path of a file you would like to send
file = ""
# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peerID)


def on_message_received(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conversation_name}:", message.decode(
        "utf-8"))


# Starting a conversation with name "test-con",
# where the peer is listening for conversations on a ConversationListener called "general_listener",
# waiting for the peer to join the conversation until executing the next line of code
print("Setting up conversation...")
conv = ipfs_datatransmission.start_conversation(
    "test-con", peerID, "general_listener", on_message_received)
print("Peer joined conversation.")
print("Sending file...")


def progress_handler(progress):
    print(f"{round(progress*100)}%")


conv.transmit_file(file, "testfile".encode(), progress_handler=progress_handler)
conv.say("Hello there!".encode('utf-8'))
print("Listening for reply...")
data = conv.listen()
print("Peer replied: ", data)
conv.say("Bye!".encode('utf-8'))
data = conv.listen(timeout=200)
if data:
    print("Received data: ", data)
else:
    print("Received no more messages after waiting 5 seconds.")
conv.terminate()
