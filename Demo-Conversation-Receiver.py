"""
This script demonstrates, together with Demo-Conversation-Starter,
the usage of the IPFS_DataTransmission.Conversation class.

Run this script, run Demo-Conversation-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

import time
import IPFS_DataTransmission


def NewConvHandler(conversation_name, peerID):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conversation_name)

    def OnMessageReceived(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conversation_name}:", message.decode(
            "utf-8"))
        conversation.Say("Hi back".encode("utf-8"))
    conv = IPFS_DataTransmission.Conversation()
    conv.Join(conversation_name, peerID, conversation_name)#, OnMessageReceived)
    print("joined")
    data = conv.Listen()
    print("Received data: ", data)
    # time.sleep(1)
    conv.Say("Hi back".encode("utf-8"))
    data = conv.Listen()
    print("Received data: ", data)


conv_lis = IPFS_DataTransmission.ListenForConversations(
    "general_listener", NewConvHandler)

# endless loop to stop program from terminating
while True:
    time.sleep(1)
