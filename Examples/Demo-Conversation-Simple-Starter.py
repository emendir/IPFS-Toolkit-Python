"""
This script demonstrates, together with Demo-Conversation-Simple-Receiver,
the basic usage of the ipfs_datatransmission.Conversation class.

Run Demo-Conversation-Simple-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below,
and then run this script.
"""

import time
import ipfs_datatransmission
import ipfs_api


# insert your peer's IPFS ID here
peer_id = ""

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peer_id)


def on_message_received(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conv_name}:", message.decode(
        "utf-8"))
    if message.decode() == "Seeya!":
        conversation.say("Wait!".encode('utf-8'))
        # conversation.say("This is so cool!".encode('utf-8'))
        # conversation.say("Whatever then...".encode('utf-8'))

        conversation.say("Bye!".encode('utf-8'))
        data = conversation.listen(timeout=5)
        conversation.close()


# Starting a conversation with name "test-con",
# where the peer is listening for conversations on a ConversationListener called "general_listener",
# waiting for the peer to join the conversation until executing the next line of code
print("Setting up conversation...")
conv = ipfs_datatransmission.start_conversation(
    "test-con", peer_id, "general_listener", on_message_received)
print("Peer joined conversation.")
time.sleep(1)
conv.say("Hello there!".encode('utf-8'))

time.sleep(30)
conv.terminate()
