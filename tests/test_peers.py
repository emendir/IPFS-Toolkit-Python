import shutil
import time
import threading
from datetime import datetime
import sys
import os
from termcolor import colored
from docker_container import DockerContainer
if True:
    sys.path.insert(0, "..")
    import ipfs_api
    from ipfs_peers import Peer, PeerMonitor


DELETE_ALL_IPFS_DOCKERS = True
REBUILD_DOCKER = False

if os.path.exists("testfile"):
    file_path = "testfile"
else:
    file_path = input("Enter filepath for test transmission file (~10MB): ")

if DELETE_ALL_IPFS_DOCKERS:
    try:
        os.system("docker stop $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1; docker rm $(docker ps --filter 'ancestor=emendir/ipfs-toolkit' -aq)  >/dev/null 2>&1")
    except:
        pass


if REBUILD_DOCKER:
    from build_docker import build_docker
    build_docker(verbose=False)

docker_peer = DockerContainer("IPFS-Toolkit-Test")
peer_id = docker_peer.ipfs_id


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


monitor1_config_path = "monitor1_config.json"
monitor2_config_path = "monitor2_config.json"


def test_create_peer_monitor():
    if os.path.exists(monitor1_config_path):
        os.remove(monitor1_config_path)
    global monitor
    monitor = PeerMonitor(monitor1_config_path)
    monitor.register_contact_event(peer_id)

    print(mark(validate_peer_object(monitor.peers()[0])), "Create PeerMonitor")


def test_load_peer_monitor():
    global monitor2
    monitor.save()
    time.sleep(6)   # wait so that the test_autoconnect can be sure of its result
    if os.path.exists(monitor2_config_path):
        os.remove(monitor2_config_path)
    shutil.copy(monitor1_config_path, monitor2_config_path)
    monitor2 = PeerMonitor(monitor2_config_path)
    print(mark(monitor.peers()[0].serialise() ==
          monitor2.peers()[0].serialise()), "Load PeerMonitor")


def test_autoconnect():
    monitor2.forget_after_hrs = 0.0025    # 9s
    monitor2.connection_attempt_interval_sec = 5
    print(mark((monitor2.peers()[0].multiaddrs()[0][1] -
          datetime.utcnow()).total_seconds() < 1), "Autoconnection")


def test_entry_deletion():
    # wait one cycle, make sure peer isn't forgotten while it is still online
    time.sleep(6)
    print(mark(len(monitor2.peers()) == 1), "Forget peer not malfunctioning")
    # do another autoconnect test, making sure the mutltiaddr date was updated
    print(mark((monitor2.peers()[0].multiaddrs()[0][1] -
          datetime.utcnow()).total_seconds() < 3), "Autoconnection still working")
    # take peer offline, then wait some cycles and enough time for the IPFS
    # daemon to realise the connection loss and check if peer was forgoten
    docker_peer.stop()
    time.sleep(60)
    forget_success = len(monitor2.peers()) == 0
    print(mark(forget_success), "Forget peer working")
    if not forget_success:
        print(ipfs_api.is_peer_connected(monitor2.peers()[0].peer_id()))
        print("Multiaddrs: ", monitor2.peers()[0].multiaddrs())


def test_terminate():
    monitor.terminate()
    monitor2.terminate()
    docker_peer.terminate()
    time.sleep(10)


def test_thread_cleanup():
    """
    tests that no unterminated threads remain running.
    """
    time.sleep(2)
    success = len(threading.enumerate()) == 1
    print(mark(success), "thread cleanup")


def run_tests():
    print("Starting tests...")
    test_peer_creation()
    test_peer_connection()
    test_serialisation()
    test_create_peer_monitor()
    test_load_peer_monitor()
    test_autoconnect()
    test_entry_deletion()
    test_terminate()
    test_thread_cleanup()


if __name__ == "__main__":
    run_tests()
