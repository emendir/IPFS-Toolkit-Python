"""
This script demonstrates, together with Demo-Conversation-Encrypted-Starter,
the usage of the ipfs_datatransmission.Conversation class.

Run this script, run Demo-Conversation-Encrypted-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time
import ipfs_datatransmission

# import an encryption library (any can be used, as long as they give you simple encryption and decryption functions for bytearays)
from Cryptem import Crypt
crypt = Crypt("mypassword")  # cryptography object that contains encryption and decryption functions


def new_conv_handler(conv_name, peer_id):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conv_name)

    def on_message_received(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conv_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Bye!":
            conversation.close()
        conv.say("Bye!".encode("utf-8"))

    conv = ipfs_datatransmission.join_conversation(
        conv_name,
        peer_id,
        conv_name,
        on_message_received,
        encryption_callbacks=(crypt.Encrypt, crypt.Decrypt)
    )
    print("Joined")

    conv.say("Hi!".encode("utf-8"))


conv_lis = ipfs_datatransmission.listen_for_conversations(
    "general_listener", new_conv_handler)
print("Set up listener")
# endless loop to stop program from terminating
while True:
    time.sleep(1)

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.terminate()
