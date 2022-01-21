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
        return
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conversation_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Bye!":
            conversation.Close()

    def OnFileReceived(conversation, filepath, metadata):
        print("Received file", filepath)

    conv = IPFS_DataTransmission.Conversation()
    conv.Join(conversation_name, peerID, conversation_name, OnMessageReceived, OnFileReceived)
    file = conv.ListenForFile(5)
    print("FILELISTEN", file)
    print("joined")
    data = conv.Listen()
    print("Received data: ", data)
    conv.Say("Hi back".encode("utf-8"))
    data = conv.Listen()
    print("Received data: ", data)


conv_lis = IPFS_DataTransmission.ListenForConversations(
    "general_listener", NewConvHandler)
print("Set up listener")
# endless loop to stop program from terminating
while True:
    time.sleep(1)

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.Terminate()
