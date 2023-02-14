import time
if True:
    time.sleep(5)
    import ipfs_datatransmission
"""
This script demonstrates, together with Demo-Conversation-Full-Starter,
the advanced usage of the ipfs_datatransmission.Conversation class.

Run this script, run Demo-Conversation-Full-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""

# ipfs_datatransmission.print_log = True
# ipfs_datatransmission.print_log_conversations = True
# ipfs_datatransmission.print_log_files = True


def new_conv_handler(conversation_name, peerID):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conversation_name)

    def on_message_received(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conversation_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Bye!":
            conversation.terminate()

    def on_file_received(conversation, filepath, metadata):
        print("Received file", filepath)

    def progress_handler(progress):
        print(str(round(progress*100))+"%")

    conv = ipfs_datatransmission.Conversation()
    conv.join(conversation_name, peerID, conversation_name, on_message_received,
              on_file_received, file_progress_callback=progress_handler, dir="/opt")
    print("Waiting for file...")
    data = conv.listen_for_file(200)
    if data:
        file = data['filepath']
        metadata = data['metadata']
    print("Received file:", file, metadata)
    data = conv.listen()
    print("Peer said:", data)
    conv.say("Hi back".encode("utf-8"))
    data = conv.listen()
    print("Received data: ", data)


conv_lis = ipfs_datatransmission.listen_for_conversations(
    "general_listener", new_conv_handler)
print("Set up listener")
# input()
while True:
    # endless loop to stop program from terminating
    time.sleep(1)

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.terminate()
