"""
This script demonstrates, together with Demo-Conversation-Simple-Starter,
the basic usage of the IPFS_DataTransmission.Conversation class.

Run this script, run Demo-Conversation-Simple-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import threading
import time
import IPFS_DataTransmission


def NewConvHandler(conversation_name, peerID):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conversation_name)

    def OnMessageReceived(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conversation_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Hello there!":
            conversation.Say("Seeya!".encode())
        if message.decode("utf-8") == "Bye!":
            conversation.Close()
        else:
            conversation.Say("I dare say!".encode("utf-8"))

    conv = IPFS_DataTransmission.Conversation()
    conv.Join(conversation_name, peerID, conversation_name, OnMessageReceived)
    print("Joined")

    conv.Say("Hi!".encode("utf-8"))


conv_lis = IPFS_DataTransmission.ListenForConversations(
    "general_listener", NewConvHandler)
print("Set up listener")
# endless loop to stop program from terminating
input()

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.Terminate()
