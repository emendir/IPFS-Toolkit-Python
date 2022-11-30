import IPFS_DataTransmission
import time
"""
This script demonstrates, together with Demo-Conversation-Full-Starter,
the advanced usage of the IPFS_DataTransmission.Conversation class.

Run this script, run Demo-Conversation-Full-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""


def NewConvHandler(conversation_name, peerID):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conversation_name)

    def OnMessageReceived(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conversation_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Bye!":
            conversation.Close()

    def OnFileReceived(conversation, filepath, metadata):
        print("Received file", filepath)
    def ProgressHandler(progress):
        print(str(round(progress*100))+"%")

    conv = IPFS_DataTransmission.Conversation()
    conv.Join(conversation_name, peerID, conversation_name, OnMessageReceived,
              OnFileReceived, file_progress_callback=ProgressHandler, dir="/home/ubuntu-vm/Desktop")
    print("Waiting for file...")
    data = conv.ListenForFile(200)
    if data:
        file = data['filepath']
        metadata = data['metadata']
    print("Received file:", file, metadata)
    data = conv.Listen()
    print("Peer said:", data)
    conv.Say("Hi back".encode("utf-8"))
    data = conv.Listen()
    print("Received data: ", data)


conv_lis = IPFS_DataTransmission.ListenForConversations(
    "general_listener", NewConvHandler)
print("Set up listener")
# endless loop to stop program from terminating
input()

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.Terminate()
