from time import sleep
from ipfs_node import IpfsNode
import os
import shutil
import tempfile

import _testing_utils
import pytest
from _testing_utils import mark

import ipfs_tk_transmission
import ipfs_tk_generics
import ipfs_tk_transmission.config
import logging
import ipfs_tk_transmission.conversations

print(ipfs_tk_transmission.conversations.__file__)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger = logging.getLogger("IPFS-TK-Conversations")
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.debug("HELLO THERE")


_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)),
    module=ipfs_tk_transmission,
)
_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)),
    module=ipfs_tk_generics,
)
DATA_TO_SEND = "Hello there!".encode()
TRANSMISSION_NAME = "ipfs_tk_test_node_transm_simple"

received_data: list[bytes] = []
SALUTATION_MESSAGE = "G'day!".encode()
SALUTATION_MESSAGE_JOIN = "How're you going?".encode()
MESSAGE_1 = "Hello there!".encode("utf-8")
REPLY_1 = "Hi!".encode()
MESSAGE_2 = "It's working, it's working!".encode("utf-8")
REPLY_2 = "Seeya soon!".encode("utf-8")
MESSAGE_3 = "Bye!".encode("utf-8")


def prepare():
    dir_rec = tempfile.mkdtemp()
    dir_sen = tempfile.mkdtemp()
    # print("Receiver kubo logs:", os.path.join(dir_rec, "kubo.log"))
    # print("Sender kubo logs:", os.path.join(dir_sen, "kubo.log"))
    pytest.ipfs_receiver = IpfsNode(dir_rec)

    pytest.ipfs_sender = IpfsNode(dir_sen)


def test_find_peer():
    multi_addr = f"{pytest.ipfs_receiver.get_addrs()[0]}/p2p/{
        pytest.ipfs_receiver.peer_id
    }"
    pytest.ipfs_sender.peers.connect(multi_addr)
    found_peer = pytest.ipfs_sender.peers.find(pytest.ipfs_receiver.peer_id)
    mark(found_peer, "Found peer")


FILE_MESSAGE = "Here's a file:".encode()
TEST_FILE = __file__


def test_messages():
    node_listener_received_messages: list[bytes] = []

    def new_conv_handler(conv_name, peer_id, salutation_start):
        """Eventhandler for when we join a new conversation."""
        print("Joining a new conversation:", conv_name)
        print(f"Salutation: {salutation_start}")

        def on_message_received(conversation, message):
            """Eventhandler for when the other peer says something in the conversation."""
            print(
                f"Received message on {conversation.conv_name}:",
                message.decode("utf-8"),
            )
            node_listener_received_messages.append(message)
            if message == MESSAGE_1:
                conversation.say(REPLY_1)
            elif message == MESSAGE_2:
                conversation.say(REPLY_2)
            elif message == MESSAGE_3:
                conversation.close()
            else:
                print(f"Received unexpected message: {message}")

        if salutation_start != SALUTATION_MESSAGE:
            print(
                f"Received unexpected salutation message: {salutation_start}"
            )
        conv = pytest.ipfs_receiver.join_conversation(
            conv_name,
            peer_id,
            conv_name,
            on_message_received,
            salutation_message=SALUTATION_MESSAGE_JOIN,
        )
        conv.salutation_start = salutation_start
        print("Joined")

    pytest.conv_lis = pytest.ipfs_receiver.listen_for_conversations(
        "general_listener", new_conv_handler
    )
    print("Set up listener")
    node_sender_received_messages: list[bytes] = []

    def sender_on_message_received(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(
            f"Received message on {conversation.conv_name}:",
            message.decode("utf-8"),
        )
        node_sender_received_messages.append(message)
        if message == REPLY_1:
            conversation.say(MESSAGE_2)
            data = conversation.listen(timeout=5)
            node_sender_received_messages.append(data)
            conversation.say(MESSAGE_3)
            conversation.close()

    # Starting a conversation with name "test-con",
    # where the peer is listening for conversations on a ConversationListener called "general_listener",
    # waiting for the peer to join the conversation until executing the next line of code
    print("Setting up conversation...")
    conv = pytest.ipfs_sender.start_conversation(
        "test-con",
        pytest.ipfs_receiver.peer_id,
        "general_listener",
        sender_on_message_received,
        salutation_message=SALUTATION_MESSAGE,
    )
    print("Peer joined conversation.")
    print(conv.salutation_join)
    sleep(1)
    conv.say(MESSAGE_1)

    sleep(30)
    conv.terminate()

    pytest.conv_lis.terminate()
    mark(
        conv.salutation_start == SALUTATION_MESSAGE
        and conv.salutation_join == SALUTATION_MESSAGE_JOIN
        and MESSAGE_1 in node_listener_received_messages
        and MESSAGE_2 in node_listener_received_messages
        and MESSAGE_3 in node_listener_received_messages
        and REPLY_1 in node_sender_received_messages
        and REPLY_2 in node_sender_received_messages,
        "Conversation Messaging",
    )


def test_files():
    node_listener_received_messages: list[bytes] = []
    received_files: list[str] = []

    def new_conv_handler(conv_name, peer_id):
        """Eventhandler for when we join a new conversation."""
        print("Joining a new conversation:", conv_name)

        def on_message_received(conversation, message):
            """Eventhandler for when the other peer says something in the conversation."""
            print(
                f"Received message on {conversation.conv_name}:",
                message.decode("utf-8"),
            )
            node_listener_received_messages.append(message)
            if message == FILE_MESSAGE:
                file = conversation.listen_for_file()
                print("TEST RECEIVED FILE", file)
                received_files.append(file)

        conv = pytest.ipfs_receiver.join_conversation(
            conv_name,
            peer_id,
            conv_name,
            on_message_received,
        )
        print("Joined")

    pytest.conv_lis = pytest.ipfs_receiver.listen_for_conversations(
        "general_listener", new_conv_handler
    )
    print("Set up listener")
    node_sender_received_messages: list[bytes] = []

    def sender_on_message_received(conversation, message):
        """Eventhandler for when the other peer says something in the conversation."""
        print(
            f"Received message on {conversation.conv_name}:",
            message.decode("utf-8"),
        )
        node_sender_received_messages.append(message)

    # Starting a conversation with name "test-con",
    # where the peer is listening for conversations on a ConversationListener called "general_listener",
    # waiting for the peer to join the conversation until executing the next line of code
    print("Setting up conversation...")
    conv = pytest.ipfs_sender.start_conversation(
        "test-con",
        pytest.ipfs_receiver.peer_id,
        "general_listener",
        sender_on_message_received,
    )
    print("Peer joined conversation.")
    conv.say(FILE_MESSAGE)
    conv.transmit_file(TEST_FILE)
    print("Sent file!")
    conv.terminate()
    sleep(3)
    mark(
        FILE_MESSAGE in node_listener_received_messages
        and received_files
        and read_file(received_files[0]["filepath"]) == read_file(TEST_FILE),
        "Conversation File Transmission",
    )
    pytest.conv_lis.terminate()


def read_file(filepath: str) -> bytes | None:
    try:
        with open(filepath, "rb") as file:
            return file.read()
    except:
        return None


def cleanup():
    # when you no longer need to listen for incoming conversations, clean up resources:
    pytest.conv_lis.terminate()

    print("terminating receiver...")
    pytest.ipfs_receiver.terminate()
    print("terminating sender...")
    pytest.ipfs_sender.terminate()
    print("Finished cleaning up!")


def run_tests():
    prepare()
    test_find_peer()
    # test_messages()
    test_files()
    cleanup()


if __name__ == "__main__":
    run_tests()
