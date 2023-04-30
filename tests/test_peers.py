import time
import threading
from datetime import datetime
import sys
import os
from termcolor import colored
if True:
    sys.path.insert(0, "..")
    from ipfs_peers import Peer, PeerMonitor

peer_id = "12D3KooWBwLgwjonrHommn8zdTgTYHndDftyLbVJ48QGyEJHecZ1"
peer = None


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


def validate_peer_object(peer):
    """Only call this on peers who have had a contact event registered"""
    try:
        assert isinstance(peer.last_seen(), datetime), "Peer Object Validation: last_seen"
        assert isinstance(peer.peer_id(), str), "Peer Object Validation: peer_id"
        assert isinstance(peer.multiaddrs(), list) and isinstance(peer.multiaddrs()[0][0], str) and isinstance(
            peer.multiaddrs()[0][1], datetime), "Peer Object Validation: multiaddrs"
        return True
    except Exception as error:
        print("Peer validation error:")
        print(error)
        return False


def test_peer_creation():
    global peer
    peer = Peer(peer_id)
    peer.register_contact_event()
    print(mark(validate_peer_object(peer)), "Peer Creation")


def test_peer_connection():
    print(mark(peer.connect()), "Peer connnection")


def test_serialisation():
    global peer
    peer2 = Peer(serial=peer.serialise())
    serialisation_success = validate_peer_object(peer)

    equality_success = peer.serialise() == peer2.serialise()
    print(mark(serialisation_success and equality_success), "Serialisation")


monitor = None
monitor2 = None


monitor_config_path = "monitor_config.json"


def test_create_peer_monitor():
    if os.path.exists(monitor_config_path):
        os.remove(monitor_config_path)
    global monitor
    monitor = PeerMonitor(monitor_config_path)
    monitor.register_contact_event(peer_id)

    print(mark(validate_peer_object(monitor.peers()[0])), "Create PeerMonitor")


def test_load_peer_monitor():
    global monitor2
    monitor2 = PeerMonitor(monitor_config_path)
    print(mark(monitor.peers()[0].serialise() ==
          monitor2.peers()[0].serialise()), "Load PeerMonitor")


def test_terminate():
    monitor.terminate()
    monitor2.terminate()


def test_thread_cleanup():
    """
    tests that no unterminated threads remain running.
    """
    time.sleep(2)
    success = len(threading.enumerate()) == 1
    print(mark(success), "thread cleanup")


def run_tests():
    test_peer_creation()
    test_peer_connection()
    test_serialisation()
    test_create_peer_monitor()
    test_load_peer_monitor()
    test_terminate()
    test_thread_cleanup()


if __name__ == "__main__":
    run_tests()
