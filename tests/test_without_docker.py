import time
import os
import threading
import sys
from termcolor import colored
from datetime import datetime
if True:
    sys.path.insert(0, "..")
    import ipfs_api

DELETE_ALL_IPFS_DOCKERS = True
REBUILD_DOCKER = True


def prepare():
    if REBUILD_DOCKER:
        from build_docker import build_docker
        build_docker(verbose=False)
    if DELETE_ALL_IPFS_DOCKERS:
        try:
            os.system("docker stop $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1; docker rm $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1")
        except:
            pass


def mark(success):
    """
    Returns a check or cross character depending on the input success.
    If this script is run in pytest, this function runs an assert statement
    on the input success to signal failure to pytest, cancelling the execution
    of the rest of the calling function.
    """
    # if __name__ == os.path.basename(__file__).strip(".py"):  # if run by pytest
    #     assert success  # use the assert statement to signal failure to pytest

    if success:
        mark = colored("✓", "green")
    else:
        mark = colored("✗", "red")

    return mark


def test_pubsub():
    received_msg = bytearray()

    def on_pubsub_received(data):
        nonlocal received_msg
        received_msg = data["data"]
    sub = ipfs_api.pubsub_subscribe("autotest", on_pubsub_received)
    ipfs_api.pubsub_publish("autotest", "Hello there!".encode())
    time.sleep(5)
    success = received_msg.decode() == "Hello there!"

    print(mark(success), "PubSub communication")
    term_start = datetime.utcnow()
    sub.terminate()
    term_end = datetime.utcnow()
    term_dur = (term_end - term_start).total_seconds()
    time.sleep(30)
    success = len(threading.enumerate()) == 1
    print(mark(success), f"PubSub thread cleanup {term_dur}s")
    if not success:
        [print(x) for x in threading.enumerate()]


def run_tests():
    print("\nStarting tests for IPFS-API...")
    test_pubsub()


if __name__ == "__main__":
    test_pubsub()
