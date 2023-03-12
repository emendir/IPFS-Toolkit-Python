import ipfs_datatransmission
"""
This script demonstrates, together with Demo-Conversation-Full-Starter,
the advanced usage of the ipfs_datatransmission.Conversation class.

Run this script, run Demo-Conversation-Full-Sender.py on another computer
after reading the instructions in that script,
and of course make sure IPFS is running on both computers first.
"""


def new_conv_handler(conv_name, peer_id):
    """Eventhandler for when we join a new conversation."""
    print("Joining a new conversation:", conv_name)

    def on_message_received(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(f"Received message on {conversation.conv_name}:", message.decode(
            "utf-8"))
        if message.decode("utf-8") == "Bye!":
            conversation.close()

    def on_file_received(conversation, filepath, metadata):
        print("Received file", filepath)

    def progress_handler(progress):
        print(str(round(progress * 100)) + "%")

    conv = ipfs_datatransmission.join_conversation(
        conv_name,
        peer_id,
        conv_name,
        on_message_received,
        on_file_received,
        file_progress_callback=progress_handler,
        dir="/home/ubuntu-vm/Desktop"
    )
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
# endless loop to stop program from terminating
input()

# when you no longer need to listen for incoming conversations, clean up resources:
conv_lis.terminate()
