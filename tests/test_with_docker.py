""" DON'T FORGET TO REBUILD DOCKER CONTAINER
This script runs a docker container with which it tests various forms of
communication.

Set the 'file_path' variable below to the path of a file_path that can be transmitted
for testing, preferably of size 1-10MB.

Make sure IPFS is running on the local host (configured with
Libp2pStreamMounting and pubsub enabled) before running these tests.

If testing is interrupted and the docker container isn't closed properly
and the next time you run this script you get an error reading:
    docker: Error response from daemon: Conflict.
    The container name "/IPFS-Toolkit-Test" is already in use by container

run the following commands to stop and remove the unterminated container:
```
    docker stop $(docker ps -aqf "name=^IPFS-Toolkit-Test$")
    docker rm $(docker ps -aqf "name=^IPFS-Toolkit-Test$")
```
"""

import time
import sys
from termcolor import colored
from docker_container import DockerContainer
import os
import threading

# time in seconds to wait for file to transmit before calling test a failure
FILE_SEND_TIMEOUT = 20

TEST_CLI = False

# if you do not have any other important brenthydrive docker containers,
# you can set this to true to automatically remove unpurged docker containers
# after failed tests
DELETE_ALL_BRENTHY_DOCKERS = True


if os.path.exists("testfile"):
    file_path = "testfile"
else:
    file_path = input("Enter filepath for test transmission file (~10MB): ")

if DELETE_ALL_BRENTHY_DOCKERS:
    try:
        os.system("docker stop $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1; docker rm $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1")
    except:
        pass


if True:
    sys.path.insert(0, "..")
    if TEST_CLI:
        import ipfs_cli as ipfs_api
    else:
        import ipfs_api
    import ipfs_datatransmission


docker_peer = DockerContainer("IPFS-Toolkit-Test")


def mark(success):
    """
    Returns a check or cross character depending on the input success.
    If this script is run in pytest, this function runs an assert statement
    on the input success to signal failure to pytest, cancelling the execution
    of the rest of the calling function.
    """
    if __name__ == os.path.basename(__file__).strip(".py"):  # if run by pytest
        assert success  # use the assert statement to signal failure to pytest

    if success:
        mark = colored("✓", "green")
    else:
        mark = colored("✗", "red")

    return mark


def on_message_received(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conv_name}:", message.decode(
        "utf-8"))


file_progress = 0
conv = None


def test_find_peer():
    success = False
    for i in range(5):
        success = ipfs_api.find_peer(docker_peer.ipfs_id)
        if success:
            break

    print(mark(success), "ipfs_api.find_peer")


def progress_handler(progress):
    global file_progress
    file_progress = round(progress * 100)
    print(colored(f"{file_progress}%", "green"))


def test_create_conv():
    global conv
    # print("Setting up conversation...")
    conv = ipfs_datatransmission.start_conversation(
        "test-con", docker_peer.ipfs_id, "general_listener", on_message_received)

    success = conv != None

    print(mark(success), "ipfs_datatransmission.start_conversation")


def test_send_file():
    # print("Sending file_path...")
    conv.transmit_file(file_path, "testfile".encode(),
                       progress_handler=progress_handler)

    for i in range(FILE_SEND_TIMEOUT):
        time.sleep(1)
        if file_progress == 100:
            break
    filesize = docker_peer.run_python_code(
        f"import os;print(os.path.getsize('/opt/{os.path.basename(file_path)}'))")
    # print("Result", filesize, str(os.path.getsize(file_path)))
    success = filesize.strip("\n") == str(os.path.getsize(file_path))
    print(mark(success), "ipfs_datatransmission.transmit_file")

    success = (file_progress == 100)
    print(mark(success), "ipfs_datatransmission.transmit_file - progress_handler")


def _test_listen():
    conv.say("Hello there!".encode('utf-8'))
    print("Listening for reply...")
    data = conv.listen()
    print("Peer replied: ", data)


def test_terminate():
    conv.say("Bye!".encode('utf-8'))
    data = conv.listen(timeout=10)
    if data:
        print("Received data: ", data)
    else:
        print("Received no more messages after waiting 5 seconds.")
    conv.terminate()


def test_thread_cleanup():
    """
    Shuts down the docker container and
    tests that no unterminated threads remain running.
    """
    docker_peer.terminate()
    success = len(threading.enumerate()) == 1
    print(mark(success), "thread cleanup")

# ipfs_datatransmission.print_log = True
# ipfs_datatransmission.print_log_conversations = True
# ipfs_datatransmission.print_log_files = True


if __name__ == "__main__":
    test_find_peer()
    test_create_conv()
    test_send_file()
    test_terminate()

    # shutdown docker container and make sure no loose threads are hanging
    test_thread_cleanup()
else:
    print(__name__)
