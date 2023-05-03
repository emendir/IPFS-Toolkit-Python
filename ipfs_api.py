# This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
# process running on the computer.
# To use it you must have IPFS running on your computer.
# This wrapper uses a custom updated version of the ipfshttpclient.


from datetime import datetime
from datetime import timedelta
from termcolor import colored
import time
from threading import Event
import shutil
import tempfile
# import sys
from subprocess import Popen, PIPE
# import subprocess
import os
import os.path
# import threading
# import multiprocessing
import traceback
import ipfs_lns
import logging
from threading import Thread
try:
    import base64
    import ipfshttpclient2 as ipfshttpclient
    from base64 import urlsafe_b64decode, urlsafe_b64encode
    http_client = ipfshttpclient.client.Client()
    LIBERROR = False
except Exception as e:
    print(str(e))
    LIBERROR = True
    http_client = None
    ipfshttpclient = None
print_log = False

# List for keeping track of subscriptions to IPFS topics, so that subscriptions can be ended
subscriptions = list([])


def publish(path: str):
    """Upload a file or a directory to IPFS, returning its CID.
    Args:
        path (str): the path of the file to publish
    Returns:
        str: the IPFS content ID (CID) of the published file
    """
    result = http_client.add(path, recursive=True)
    if(type(result) == list):
        return result[-1].get("Hash")
    else:
        return result.get("Hash")


def download(cid, path="."):
    """Get the specified IPFS content, saving it to a file.
    Args:
        cid (str): the IPFS content ID (cid) of the resource to get
        path (str): (optional) the path (directory or filepath) of the saved file
    """

    # create temporary download directory
    tempdir = tempfile.mkdtemp()

    # download and save file/folder to temporary directory
    http_client.get(cid=cid, target=tempdir)

    # move file/folder from temporary directory to desired path
    shutil.move(os.path.join(tempdir, cid), path)

    # cleanup temporary directory
    shutil.rmtree(tempdir)


def read(cid):
    """Returns the textual content of the specified IPFS resource.
    Args:
        cid (str): the IPFS content ID (CID) of the resource to read
    Returns:
        str: the content of the specified IPFS resource as text
    """
    return http_client.cat(cid)


def pin(cid: str):
    """Ensure the specified IPFS resource remains available on this IPFS node.
    Args:
        cid (str): the IPFS content ID (CID) of the resource to pin
    """
    http_client.pin.add(cid)


def unpin(cid: str):
    """Allow a pinned IPFS resource to be garbage-collected and removed on this IPFS node.
    Args:
        cid (str): the IPFS content ID (CID) of the resource to unpin
    """
    http_client.pin.rm(cid)


__pins_cache = {}


def pins(cids_only: bool = False, cache_age_s: int = None):
    """Get the CIDs of files we have pinned on IPFS
    Args:
        cids_only (bool): if True, returns a plain list of IPFS CIDs
            otherwise, returns a list of dicts of CIDs and their pinning type
        cache_age_s (int): getting the of pins from IPFS can take several
            seconds. IPFS_API therefore caches each result. If the age of the
            cache is less than this parameter, the cacheed result is returned,
            otherwise the slow process of getting the latest list of pins is
            used.
    Returns:
        list(): a list of the CIDs of pinned objects. The list element type
            depends on the cids_only parameter (see above)
    """
    global __pins_cache
    if __pins_cache and cache_age_s and (datetime.utcnow() - __pins_cache['date']).total_seconds() < cache_age_s:
        data = __pins_cache['data']
    else:
        data = http_client.pin.ls()['Keys'].as_json()
        __pins_cache = {
            "date": datetime.utcnow(),
            "data": data
        }
    if cids_only:
        return list(data.keys())
    else:
        return data


def create_ipns_record(name: str, type: str = "rsa", size: int = 2048):
    """Create an IPNS record (eqv. IPNS key).
    Args:
        name (str): the name of the record/key (in the scope of this IPFS node)
        type (str): the cryptographic algorithm behind this key's security
        size (int): the length of the key
    """
    result = http_client.key.gen(key_name=name, type=type, size=size)
    if isinstance(result, list):
        return result[-1].get("Id")
    else:
        return result.get("Id")


def update_ipns_record_from_cid(record_name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    """Assign IPFS content to an IPNS record.
    Args:
        record_name (str): the name of the IPNS record (IPNS key) to be updated
        cid (str): the IPFS content ID (CID) of the content to assign to the IPNS record
        ttl (str): Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        lifetime (str): Time duration that the record will be valid for.
                                Default: 24h.
    """
    http_client.name.publish(ipfs_path=cid, key=record_name,
                             ttl=ttl, lifetime=lifetime)


def update_ipns_record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    """Publish a file to IPFS and assign it to an IPNS record.
    Args:
        record_name (str): the name of the IPNS record (IPNS key) to be updated
        path (str): the path of the file to assign to the IPNS record
        ttl (str): Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        lifetime (str): Time duration that the record will be valid for.
                                Default: 24h.
    """
    cid = publish(path)
    update_ipns_record_from_cid(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def resolve_ipns_key(ipns_key, nocache=False):
    """Get the IPFS CID of the given IPNS record (IPNS key)
    Args:
        ipns_key: the key of the IPNS record to lookup
        nocache: whether or not to ignore this IPFS nodes cached memory of IPNS keys
    Returns:
        str: the IPFS CID associated with the IPNS key
    """
    return http_client.name.resolve(name=ipns_key, nocache=nocache).get("Path")


def download_ipns_record(ipns_key, path="", nocache=False):
    """Get the specified IPFS content, saving it to a file.
    Args:
        ipns_key (str): the key of the IPNS record to get
        path (str): (optional) the path (directory or filepath) of the saved file
        nocache: whether or not to ignore this IPFS nodes cached memory of IPNS keys
    """
    return download(resolve_ipns_key(ipns_key, nocache=nocache), path)


def read_ipns_record(ipns_key, nocache=False):
    """Returns the textual content of the specified IPFS resource.
    Args:
        ipns_key (str): the key of the IPNS record to read
    Returns:
        str: the content of the specified IPFS resource as text
    """
    return read(resolve_ipns_key(ipns_key, nocache=nocache))


def my_id():
    """Returns this IPFS node's peer ID.
    Returns:
        str: the peer ID of this node
    """
    return http_client.id().get("ID")


def is_ipfs_running():
    """Checks whether or not the IPFS daemon is currently running.
    Returns:
        bool: whether or not the IPFS daemon is currently running
    """
    return len(my_multiaddrs()) > 0


def my_multiaddrs():
    """Returns this IPFS node's peer ID.
    Returns:
        str: the peer ID of this node
    """
    return http_client.id().get("Addresses")


def list_peers():
    """Returns a list of the IPFS multiaddresses of the other nodes
    this node is connected to.
    Returns:
        list(str): a list of the IPFS multiaddresses of the other nodes
        this node is connected to
    """
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8').strip("\n"))

    return peers


def list_peer_multiaddrs():
    print(colored("IPFS_API: DEPRECATED: This function (ifps_api.list_peer_multiaddrs) has been renamed to ipfs_api.list_peers to avoid confusion with the new get_peer_multiaddrs function.", "yellow"))
    return list_peers()


def get_peer_multiaddrs(peer_id):
    """Returns the multiaddresses (without the IPFS CID) via which we can reach
    the specified peer.
    Append /p2p/PEER_ID to these multiaddress parts to turn them into complete
    multiaddresses.

    Args:
        peer_id (str): the IPFS ID of the peer to lookup

    Returns:
        list(str): the multiaddresses (without the IPFS CID) via which we can
        reach the given peer
    """
    try:
        response = http_client.dht.findpeer(peer_id)
        return response.get("Responses")[0].get("Addrs")
    except:
        return []


def connect_to_peer(multiaddr):
    """Tries to connect to a peer given its multiaddress.
    Returns:
        bool: success
    """
    try:
        response = http_client.swarm.connect(multiaddr)
        if response.get("Strings")[0][-7:] == "success":
            return True
        return False
    except:
        return False


def find_peer(peer_id: str):
    """Try to connect to the specified IPFS node.
    Args:
        peer_id (str): the IPFS peer ID of the node to connect to
    Returns:
        str: the multiaddress of the connected node
    """
    try:
        response = http_client.dht.findpeer(peer_id)
        if(len(response.get("Responses")[0].get("Addrs")) > 0):
            return response
    except:
        return None


def is_peer_connected(peer_id, ping_count=1):
    """Tests the connection to the given IPFS peer.
    Args:
        peer_id (str): the IPFS ID of the peer to test
        count (int): (optional, default 1) the number of pings to send
    Returns:
        bool: whether or not the peer is connected
    """
    responses = http_client.ping(peer_id, count=ping_count)
    return responses[-1]['Success']


def find_providers(cid):
    """Lookup/find out which IPFS nodes provide the file with the given CID
    (including onesself).
    E.g. to check if this computer hosts a file with a certain CID:
    def DoWeHaveFile(cid:str):
        ipfs_api.my_id() in ipfs_api.find_providers(cid)
    Args:
        cid (str): cid (str): the IPFS content ID (CID) of the resource to look up
    Returns:
        list: the peer IDs of the IPFS nodes who provide the file
    """
    responses = http_client.dht.findprovs(cid)
    peers = []
    for response in responses:
        if not isinstance(response, ipfshttpclient.client.base.ResponseBase):
            continue
        if response['Type'] == 4:
            for resp in response['Responses']:
                if resp['ID'] and resp['ID'] not in peers:
                    peers.append(resp['ID'])
    return peers


def create_tcp_listening_connection(name: str, port: int):
    """Open a listener TCP connection for IPFS' libp2p stream-mounting (port-forwarding).
    TCP traffic coming from another peer via this connection is forwarded
    to the specified port on localhost.
    Args:
        name (str): the name of the connection (starts with /x/)
        port (int): the local TCP port number to forward incoming traffic to
    """
    if name[:3] != "/x/":
        name = "/x/" + name
    http_client.p2p.listen(name, "/ip4/127.0.0.1/tcp/" + str(port))


def create_tcp_sending_connection(name: str, port, peerID):
    """Open a sending TCP connection for IPFS' libp2p stream-mounting (port-forwarding).
    TCP traffic sent to the specified port on localhost will be fowarded
    to the specified peer via this connection.
    Args:
        name (str): the name of the connection (starts with /x/)
        port (int): the local TCP port number from which to forward traffic
    """
    if name[:3] != "/x/":
        name = "/x/" + name
    http_client.p2p.forward(name, "/ip4/127.0.0.1/tcp/"
                            + str(port), "/p2p/" + peerID)


def close_all_tcp_connections(listeners_only=False):
    """Close all libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        listeners_only (bool): if set to True, only listening connections are closed
    """
    if listeners_only:
        http_client.p2p.close(listenaddress="/p2p/" + my_id())
    else:
        http_client.p2p.close(True)


def close_tcp_sending_connection(name: str = None, port: str = None, peer_id: str = None):
    """Close specific sending libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        name (str): the name of the connection to close
        port (str): the local forwarded TCP port of the connection to close
        peer_id (str): the target peer_id of the connection to close
    """
    if name and name[:3] != "/x/":
        name = "/x/" + name
    if port and isinstance(port, int):
        listenaddress = f"/ip4/127.0.0.1/tcp/{port}"
    else:
        listenaddress = port
    if peer_id and peer_id[:5] != "/p2p/":
        targetaddress = "/p2p/" + peer_id
    else:
        targetaddress = peer_id
    http_client.p2p.close(False, name, listenaddress, targetaddress)


def close_tcp_listening_connection(name: str = None, port: str = None):
    """Close specific listening libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        name (str): the name of the connection to close
        port (str): the local listening TCP port of the connection to close
    """
    if name and name[:3] != "/x/":
        name = "/x/" + name
    if port and isinstance(port, int):
        targetaddress = f"/ip4/127.0.0.1/tcp/{port}"
    else:
        targetaddress = port
    http_client.p2p.close(False, name, None, targetaddress)


def check_peer_connection(id, name=""):
    """Try to connect to the specified peer, and stores its multiaddresses in ipfs_lns.
    Args:
        id (str): the IPFS PeerID or the ipfs_lns name  of the computer to connect to
        name (str): (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    contact = ipfs_lns.get_contact(id)
    if not contact:
        contact = ipfs_lns.add_contact(id, name)
    return contact.check_connection()


class PubsubListener():
    """Listener object for PubSub subscriptions."""
    _terminate = False
    __listening = False
    sub = None
    _REFRESH_RATE = 5  # seconds. How often the pubsub HTTP listener ist restarted, also the maximum duration termination can take

    def __init__(self, topic, eventhandler):
        self.topic = topic
        self.eventhandler = eventhandler
        self.listen()

    def _listen(self):
        if self.__listening:
            return
        self.__listening = True
        """blocks the calling thread"""
        while not self._terminate:
            try:
                if int(http_client.version()["Version"].split(".")[1]) >= 11:
                    with http_client.pubsub.subscribe(self.topic, timeout=self._REFRESH_RATE) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = {
                                "senderID": message["from"],
                                "data": _decode_base64_url(message["data"]),
                            }

                            Thread(
                                target=self.eventhandler,
                                args=(data,),
                                name="ipfs_api.PubsubListener-eventhandler"
                            ).start()
                else:
                    with http_client.pubsub.subscribe_old(self.topic) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = str(base64.b64decode(
                                str(message).split('\'')[7]), "utf-8")
                            Thread(
                                target=self.eventhandler,
                                args=(data,),
                                name="ipfs_api.PubsubListener-eventhandler"
                            ).start()
            except:
                pass
                # print(f"IPFS API Pubsub: restarting sub {self.topic}")
        self.__listening = False

    def listen(self):
        self._terminate = False
        self.listener_thread = Thread(
            target=self._listen, args=(), name="ipfs_api.PubsubListener")
        self.listener_thread.start()

    def terminate(self):
        """Stop this PubSub subscription, stop listening for data.
        May let one more pubsub message through
        Takes up to self._REFRESH_RATE seconds to complete.
        """
        self._terminate = True
        if self.sub:
            self.sub.close()


def pubsub_publish(topic, data):
    """Publishes te specified data to the specified IPFS-PubSub topic.
    Args:
        topic (str): the name of the IPFS PubSub topic to publish to
        data (str/bytearray): either the filepath of a file whose
            content should be published to the pubsub topic,
            or the raw data to be published as a string or bytearray.
            When using an older version of IPFS < v0.11.0 however,
            only plain data as a string is accepted.
    """
    if int(http_client.version()["Version"].split(".")[1]) < 11:
        return http_client.pubsub.publish_old(topic, data)

    if isinstance(data, str) and not os.path.exists(data):
        data = data.encode()
    if isinstance(data, bytes) or isinstance(data, bytearray):
        with tempfile.NamedTemporaryFile() as tp:
            tp.write(data)
            tp.flush()
            http_client.pubsub.publish(topic, tp.name)
    else:
        http_client.pubsub.publish(topic, data)


def pubsub_subscribe(topic, eventhandler):
    """
    Listens to the specified IPFS PubSub topic, calling the eventhandler
    whenever a message is received, passing the message data and its sender
    to the eventhandler.
    Args:
        topic (str): the name of the IPFS PubSub topic to publish to
        eventhandler (function): the function to be executed whenever a message is received.
                            The eventhandler parameter is a dict with the keys 'data' and 'senderID',
                            except when using an older version of IPFS < v0.11.0,
                            in which case only the message is passed as a string.
    Returns:
        PubsubListener: listener object which can  be terminated with the .terminate() method (and restarted with the .listen() method)
    """
    return PubsubListener(topic, eventhandler)


def pubsub_peers(topic: str):
    """Looks up what IPFS nodes we are connected to who are listening on the given topic.
    Returns:
        list: peers we are connected to on the specified pubsub topic
    """
    return http_client.pubsub.peers(topic=_encode_base64_url(topic.encode()))["Strings"]


def _decode_base64_url(data: str):
    """Performs the URL-Safe multibase decoding required by some functions (since IFPS v0.11.0) on strings"""
    if isinstance(data, bytes):
        data = data.decode()
    data = str(data)[1:].encode()
    missing_padding = len(data) % 4
    if missing_padding:
        data += b'=' * (4 - missing_padding)
    return urlsafe_b64decode(data)


def _encode_base64_url(data: bytearray):
    """Performs the URL-Safe multibase encoding required by some functions (since IFPS v0.11.0) on strings"""
    if isinstance(data, str):
        data = data.encode()
    data = urlsafe_b64encode(data)
    while data[-1] == 61 and data[-1]:
        data = data[:-1]
    data = b'u' + data
    return data


def wait_till_ipfs_is_running(timeout_sec=None):
    """Waits till it can connect to the local IPFS daemon's HTTP-interface.
    Args:
        timeout_sec (int): maximum time to wait for. If this duration is,
                            exceeded, a TimeoutError is raised.
    """
    count = 0
    while True:
        try:
            if is_ipfs_running():
                return
        except ipfshttpclient.exceptions.ConnectionError as error:
            pass
        time.sleep(1)
        count += 1
        if timeout_sec and count == timeout_sec:
            raise TimeoutError()


def try_run_ipfs():
    """Tries to use the IPFS CLI to run the local IPFS daemon with PubSub,
    like manually executing `ipfs daemon --enable-pubsub-experiment`
    """
    from ipfs_cli import try_run_ipfs as _try_run_ipfs
    _try_run_ipfs()


if LIBERROR:    # if not all modules needed for the ipfs_http_client library were loaded
    print("Falling back to IPFS CLI because our HTTP client isn't working;\nNot all modules required by the http-connection could be loaded.")
    from ipfs_cli import *
