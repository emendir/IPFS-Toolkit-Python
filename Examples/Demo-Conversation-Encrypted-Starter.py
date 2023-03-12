"""
This script demonstrates, together with Demo-ConversationEncrypted-Receiver,
the usage of the ipfs_datatransmission.Conversation class' encryption feature.

Run Demo-ConversationEncrypted-Receiver.py on another computer,
make sure IPFS is running on both computers first,
paste the other's IPFS ID in the peer_id variable below,
and then run this script.
"""

import time
import ipfs_datatransmission
import ipfs_api
from Cryptem import Crypt

crypt = Crypt("mypassword")

# insert your peer's IPFS ID here
peer_id = ""

# making sure our IPFS node finds the receiver computer on the IP layer of the internet
ipfs_api.find_peer(peer_id)


def on_message_received(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conv_name}:", message.decode(
        "utf-8"))
    if message.decode() == "Bye!":
        conv.say("Wait!".encode('utf-8'))
        conv.say("This is so cool!".encode('utf-8'))
        conv.say("Whatever then...".encode('utf-8'))

        conv.say("Bye!".encode('utf-8'))
        data = conv.listen(timeout=5)
        print(data)
        conv.close()


# Starting a conversation with name "test-con",
# where the peer is listening for conversations on a ConversationListener called "general_listener",
# waiting for the peer to join the conversation until executing the next line of code
print("Setting up conversation...")
conv = ipfs_datatransmission.start_conversation(
    "test-con", peer_id, "general_listener", on_message_received, encryption_callbacks=(crypt.Encrypt, crypt.Decrypt))
print("Peer joined conversation.")
time.sleep(1)
conv.say("Hello there!".encode('utf-8'))

while True:
    time.sleep(1)
