from kubo_python import IpfsNode
import os
import shutil
import tempfile

import _testing_utils
import pytest
from _testing_utils import mark

import ipfs_tk_transmission
import ipfs_tk_generics

_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=ipfs_tk_transmission
)
_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=ipfs_tk_generics
)

DATA_TO_SEND = "Hello there!".encode()
TRANSMISSION_NAME = "ipfs_tk_test_node_transm_simple"

received_data: list[bytes] = []


def on_receive(data, peer_id):
    """Eventhandler to handle received data"""
    print("Received data transmission!")
    print(data.decode("utf-8"))
    received_data.append(data)


ipfs_receiver = IpfsNode()

# starting to listen for incoming data transmissions
listener = ipfs_receiver.listen_for_transmissions(
    TRANSMISSION_NAME, on_receive
)


ipfs_sender = IpfsNode()


found_peer = ipfs_sender.peers.find(ipfs_receiver.peer_id)
mark(found_peer, "Found peer")
if found_peer:

    # sending data to peer, waiting for the transmission to complete until executing the next line of code
    if ipfs_sender.transmit_data(
        DATA_TO_SEND, ipfs_receiver.peer_id, TRANSMISSION_NAME
    ):
        print("Sent Data!!")
    else:
        print("Failed to send data.")

    mark(DATA_TO_SEND in received_data, "Simple DataTransmission")

listener.terminate()

ipfs_receiver.terminate()
ipfs_sender.terminate()
