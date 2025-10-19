# This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
# process running on the computer.
# To use it you must have IPFS running on your computer.
# This wrapper uses a custom updated version of the ipfshttpclient.

from ipfs_tk_generics.peers import SwarmFiltersUpdateError
from ipfs_tk_generics.pubsub import BasePubsubListener
import socket
from urllib.parse import ParseResult
from urllib.parse import urlparse
from io import BytesIO
from threading import Thread
import ipfs_lns
import traceback
import os.path
import os
from subprocess import Popen, PIPE
import tempfile
import shutil
from threading import Event
import time
from termcolor import colored
from datetime import timedelta
import base64
import ipfs_remote.ipfshttpclient2 as ipfshttpclient
from base64 import urlsafe_b64decode, urlsafe_b64encode
from ipfs_remote import IpfsRemote

if True:
    from ipfs_remote.files import USE_IPFS_CONTENT_CACHE
    from ipfs_remote.pubsub import PubsubListener

    client = IpfsRemote("/dns/localhost/tcp/5001/http")
else:
    from ipfs_node import IpfsNode

    USE_IPFS_CONTENT_CACHE = False
    from ipfs_node.ipfs_pubsub import IPFSSubscription as PubsubListener

    client = IpfsNode("/tmp/IpfsToolkitTest")


def publish(path: str):
    return client.files.publish(path)


def predict_cid(path: str):
    return client.files.predict_cid(path)


def download(cid, path="."):
    return client.files.download(cid, dest_path=path)


def read(cid: str, nocache: bool = not USE_IPFS_CONTENT_CACHE):
    return client.files.read(cid, nocache=nocache)


def pin(cid: str):
    return client.files.pin(cid)


def unpin(cid: str):
    return client.files.unpin(cid)


def remove(cid: str):
    return client.files.remove(cid)


def pins(cids_only: bool = False, cache_age_s: int = None):
    return client.files.list_pins(cids_only=cids_only, cache_age_s=cache_age_s)


def create_ipns_record(name: str, type: str = "rsa", size: int = 2048):
    return client.ipns.create_ipns_record(name, type=type, size=size)


def update_ipns_record_from_cid(
    record_name: str,
    cid: str,
    ttl: str = "24h",
    lifetime: str = "24h",
    **kwargs: ipfshttpclient.client.base.CommonArgs,
):
    return client.ipns.update_ipns_record_from_cid(
        record_name, cid, ttl=ttl, lifetime=lifetime, **kwargs
    )


def update_ipns_record(
    name: str, path, ttl: str = "24h", lifetime: str = "24h"
):
    return client.ipns.update_ipns_record(
        name, path, ttl=ttl, lifetime=lifetime
    )


def resolve_ipns_key(ipns_key, nocache=False):
    return client.ipns.resolve_ipns_key(ipns_key, nocache=nocache)


def download_ipns_record(ipns_key, path="", nocache=False):
    return client.ipns.download_ipns_record(
        ipns_key, path=path, nocache=nocache
    )


def read_ipns_record(ipns_key, nocache=False):
    return client.ipns.read_ipns_record(ipns_key, nocache=nocache)


def get_ipns_record_validity(ipns_key):
    return client.ipns.get_ipns_record_validity(ipns_key)


def my_id():
    return client.peer_id


def is_ipfs_running():
    return client.is_ipfs_running()


def my_multiaddrs():
    return client.get_addrs()


def list_peers():
    return client.peers.list_peers()


def list_peer_multiaddrs():
    return client.get_addrs()


def get_peer_multiaddrs(peer_id):
    return client.peers.find(peer_id)


def connect_to_peer(multiaddr):
    return client.peers.connect(multiaddr)


def find_peer(peer_id: str):
    return client.peers.find(peer_id)


def is_peer_connected(peer_id, ping_count=1):
    return client.peers.is_peer_connected(peer_id, ping_count=ping_count)


def find_providers(cid):
    return client.files.find_providers(cid)


def create_tcp_listening_connection(name: str, port: int):
    return client.tunnels.open_listener(name, port)


def create_tcp_sending_connection(name: str, port, peerID):
    return client.tunnels.open_sender(name, port, peerID)


def close_all_tcp_connections(listeners_only=False):
    return client.tunnels.close_all(listeners_only=False)


def close_tcp_sending_connection(
    name: str = None, port: str = None, peer_id: str = None
):
    return client.tunnels.close_sender(name=name, port=port, peer_id=peer_id)


def close_tcp_listening_connection(name: str = None, port: str = None):
    return client.tunnels.close_listener(name=name, port=port)


def check_peer_connection(id, name=""):
    """Try to connect to the specified peer, and stores its multiaddresses in ipfs_lns.
    Args:
        id (str): the IPFS PeerID or the ipfs_lns name  of the computer to connect to
        name (str): (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    print("DEPRECATED - use ipfs_peers instead")
    contact = ipfs_lns.get_contact(id)
    if not contact:
        contact = ipfs_lns.add_contact(id, name)
    return contact.check_connection()


def pubsub_publish(topic, data):
    return client.pubsub.publish(topic, data)


def pubsub_subscribe(topic, eventhandler):
    return client.pubsub.subscribe(topic, eventhandler)


def pubsub_peers(topic: str):
    return client.pubsub.list_peers(topic)


def add_swarm_filter(filter_multiaddr):
    return client.peers.add_swarm_filter(filter_multiaddr)


def rm_swarm_filter(filter_multiaddr):
    return client.peers.rm_swarm_filter(filter_multiaddr)


def get_swarm_filters():
    return client.peers.get_swarm_filters()


def wait_till_ipfs_is_running(timeout_sec=None):
    if isinstance(client, IpfsRemote):
        return client.wait_till_ipfs_is_running(timeout_sec=timeout_sec)
    else:
        return


def _ipfs_host_ip():
    return "127.0.0.1"
    return client._ipfs_host_ip()


def try_run_ipfs():
    """Tries to use the IPFS CLI to run the local IPFS daemon with PubSub,
    like manually executing `ipfs daemon --enable-pubsub-experiment`
    """
    from ipfs_cli import try_run_ipfs as _try_run_ipfs

    _try_run_ipfs()
