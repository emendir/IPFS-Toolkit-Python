"""
This script runs a docker container with which it tests various forms of
communication.

Set the 'file' variable below to the path of a file that can be transmitted
for testing, preferably of size 1-10MB.

Make sure IPFS is running on the local host (configured with
Libp2pStreamMounting and pubsub enabled) before running these tests.

If testing is interrupted and the docker container isn't closed properly
and you get an error reading:
    docker: Error response from daemon: Conflict.
    The container name "/IPFS-Toolkit-Test" is already in use by container

run the following command to stop all running containers:
    docker stop $(docker ps -aq)
And optionally to remove all containers:
    docker rm $(docker ps -aq)
"""

import time
import sys
from termcolor import colored
from docker_container import DockerContainer
import os
if True:
    sys.path.insert(0, "..")
    import ipfs_datatransmission
    import ipfs_api

docker_peer = DockerContainer("IPFS-Toolkit-Test")

# replace with the path of a file you would like to send
file = "/mnt/Uverlin/Music/Davy Jones  - Pirates of the Caribbean.mp3"


peerID = ""

while peerID == "":
    time.sleep(5)
    peerID = docker_peer.run_shell_command("ipfs id -f=\"<id>\"")
# print(peerID)


def test_find_peer():
    success = False
    for i in range(5):
        success = ipfs_api.find_peer(peerID)
        if success:
            break
    if success:
        mark = colored("✓", "green")
    else:
        mark = colored("✗", "red")
    print(mark, "ipfs_api.find_peer")
    # docker_peer.run_shell_command("python3 /opt/IPFS-Toolkit/docker_script.py&")
    # print(docker_peer.container_id)
    # time.sleep(60)


def on_message_received(conversation, message):
    """Eventhandler for when the other peer says something in the conversation."""
    print(f"Received message on {conversation.conversation_name}:", message.decode(
        "utf-8"))


file_progress = 0


def progress_handler(progress):
    global file_progress
    file_progress = round(progress*100)
    print(colored(f"{file_progress}%", "green"))


conv = None


def test_create_conv():
    global conv
    # print("Setting up conversation...")
    conv = ipfs_datatransmission.start_conversation(
        "test-con", peerID, "general_listener", on_message_received)

    if conv:
        mark = colored("✓", "green")
    else:
        mark = colored("✗", "red")
    print(mark, "ipfs_datatransmission.start_conversation")


file_send_timeout = 200


def test_send_file():
    # print("Sending file...")
    conv.transmit_file(file, "testfile".encode(), progress_handler=progress_handler)

    for i in range(file_send_timeout):
        time.sleep(1)
        if file_progress == 100:
            break
    filesize = docker_peer.run_python_code(
        f"import os;print(os.path.getsize('/opt/{os.path.basename(file)}'))")
    # print("Result", filesize, str(os.path.getsize(file)))
    if filesize.strip("\n") == str(os.path.getsize(file)):
        mark = colored("✓", "green")
        success = True
    else:
        mark = colored("✗", "red")
        success = False
    print(mark, "ipfs_datatransmission.transmit_file")
    if file_progress == 100:
        mark = colored("✓", "green")
        success = True
    else:
        mark = colored("✗", "red")
        success = False
    print(mark, "ipfs_datatransmission.transmit_file - progress_handler")


def test_listen():
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


# ipfs_datatransmission.print_log = True
# ipfs_datatransmission.print_log_conversations = True
# ipfs_datatransmission.print_log_files = True

if __name__ == "__main__":
    test_find_peer()
    test_create_conv()
    test_send_file()

docker_peer.terminate()
