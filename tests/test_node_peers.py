import os
import shutil
import threading
import time
from datetime import UTC, datetime

import _testing_utils
import peer_monitor
import pytest
from _testing_utils import mark
from ipfs_node import IpfsNode
from peer_monitor import Peer, PeerMonitor

_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=peer_monitor
)
def prepare():
    pytest.peer_1 = IpfsNode()
    pytest.peer_2 = IpfsNode()
    pytest.peer_id = pytest.peer_2.peer_id




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
    peer = Peer(pytest.peer_1, pytest.peer_2.peer_id)
    peer.register_contact_event()
    mark(validate_peer_object(peer), "Peer Creation")


def test_peer_connection():
    mark(peer.connect(), "Peer connnection")


def test_serialisation():
    global peer
    peer2 = Peer(pytest.peer_1, serial=peer.serialise())
    serialisation_success = validate_peer_object(peer)

    equality_success = peer.serialise() == peer2.serialise()
    mark(serialisation_success and equality_success, "Serialisation")


monitor = None
monitor2 = None


monitor1_config_path = "monitor1_config.json"
monitor2_config_path = "monitor2_config.json"


def test_create_peer_monitor():
    if os.path.exists(monitor1_config_path):
        os.remove(monitor1_config_path)
    global monitor
    monitor = PeerMonitor(pytest.peer_1, monitor1_config_path)
    monitor.register_contact_event(pytest.peer_2.peer_id)

    mark(validate_peer_object(monitor.peers()[0]), "Create PeerMonitor")


def test_load_peer_monitor():
    global monitor2
    monitor.save()
    time.sleep(6)   # wait so that the test_autoconnect can be sure of its result
    if os.path.exists(monitor2_config_path):
        os.remove(monitor2_config_path)
    shutil.copy(monitor1_config_path, monitor2_config_path)
    forget_after_hrs = 0.0025    # 9s
    connection_attempt_interval_sec = 5
    monitor2 = PeerMonitor(pytest.peer_1, monitor2_config_path, forget_after_hrs=forget_after_hrs,
                           connection_attempt_interval_sec=connection_attempt_interval_sec)
    mark(monitor.peers() and monitor.peers()[0].serialise() ==
          monitor2.peers()[0].serialise(), "Load PeerMonitor")


def test_autoconnect():
    mark((monitor2.peers()[0].multiaddrs()[0][1] -
          datetime.now(UTC)).total_seconds() < 1, "Autoconnection")


def test_find_all_peers():
    success = False
    try:
        monitor.find_all_peers()
        success = True
    except Exception as error:
        print(error)
    mark(success, "find_all_peers")


def test_entry_deletion():
    # wait one cycle, make sure peer isn't forgotten while it is still online
    time.sleep(6)
    mark(len(monitor2.peers()) == 1, "Forget peer not malfunctioning")
    # do another autoconnect test, making sure the mutltiaddr date was updated
    mark(monitor2.peers() and (monitor2.peers()[0].multiaddrs()[0][1] -
          datetime.now(UTC)).total_seconds() < 3, "Autoconnection still working")
    # take peer offline, then wait some cycles and enough time for the IPFS
    # daemon to realise the connection loss and check if peer was forgoten
    pytest.peer_2.terminate()
    time.sleep(20)
    forget_success = len(monitor2.peers()) == 0
    mark(forget_success, "Forget peer working")
    if not forget_success:
        print(pytest.peer_1.peers.is_connected(monitor2.peers()[0].peer_id()))
        print("Multiaddrs: ", monitor2.peers()[0].multiaddrs())


def test_terminate():
    monitor.terminate(True)
    monitor2.terminate()
    pytest.peer_1.terminate()
    pytest.peer_2.terminate()
    time.sleep(10)


def test_thread_cleanup():
    """Tests that no unterminated threads remain running.
    """
    time.sleep(2)
    success = len(threading.enumerate()) == 1
    mark(success, "thread cleanup")


def run_tests():
    print("\nStarting tests for IPFS-Peers...")
    prepare()
    test_peer_creation()
    test_peer_connection()
    test_serialisation()
    test_create_peer_monitor()
    test_find_all_peers()
    test_load_peer_monitor()
    test_autoconnect()
    test_entry_deletion()
    test_terminate()
    test_thread_cleanup()


if __name__ == "__main__":
    _testing_utils.PYTEST = False
    run_tests()
