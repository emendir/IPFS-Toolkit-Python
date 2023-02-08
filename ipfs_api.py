# This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
# process running on the computer.
# To use it you must have IPFS running on your computer.
# This wrapper uses a custom updated version of the ipfshttpclient.


from termcolor import colored
import shutil
import tempfile
# import sys
from subprocess import Popen, PIPE
# import subprocess
import _thread
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
    from requests.exceptions import ConnectionError
    from base64 import urlsafe_b64decode, urlsafe_b64encode
    http_client = ipfshttpclient.client.Client()
    LIBERROR = False
except Exception as e:
    print(str(e))
    LIBERROR = True
    http_client = None
    ipfshttpclient = None
print_log = True

autostart = True
started = False
# List for keeping track of subscriptions to IPFS topics, so that subscriptions can be ended
subscriptions = list([])


def start():
    try:
        global http_client
        global started
        from ipfs_cli import run_command, ipfs_cmd
        Thread(target=run_command, args=[ipfs_cmd, "daemon", "--enable-pubsub-experiment"])

        http_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
        started = True
        logging.info("Started ipfs_api, connected to daemon")
        return True
    except Exception as e:
        logging.warning("could not connect to daemon")
        logging.debug(traceback.format_exc())
        if print_log:
            print("")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(type(e))
            if(str(e).startswith("ConnectionError: HTTPConnectionPool")):
                print("Failed to connect to the IPFS process on this machine.")
                print("Is IPFS running?")
                print("Is it listening on '/ip4/127.0.0.1/tcp/5001/http'?")
                return "IPFS not running"


def publish(path: str):
    """
    upload a file or a directory to IPFS.
    Returns the Hash of the uploaded file.
    """
    result = http_client.add(path, recursive=True)
    if(type(result) == list):
        return result[-1].get("Hash")
    else:
        return result.get("Hash")


def download(cid, path=""):
    # create temporary download directory
    tempdir = tempfile.mkdtemp()

    # download and save file/folder to temporary directory
    http_client.get(cid=cid, target=tempdir)

    # move file/folder from temporary directory to desired path
    shutil.move(os.path.join(tempdir, cid), path)

    # cleanup temporary directory
    shutil.rmtree(tempdir)


def read(ID):
    return http_client.cat(ID)


def pin(cid: str):
    http_client.pin.add(cid)


def unpin(cid: str):
    http_client.pin.rm(cid)


def create_ipns_record(name: str, type: str = "rsa", size: int = 2048):
    result = http_client.key.gen(key_name=name, type=type, size=size)
    print(result)
    if isinstance(result, list):
        return result[-1].get("Id")
    else:
        return result.get("Id")


def update_ipns_record_from_hash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    http_client.name.publish(ipfs_path=cid, key=name, ttl=ttl, lifetime=lifetime)


def update_ipns_record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    cid = publish(path)
    update_ipns_record_from_hash(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def resolve_ipns_key(ipns_id, nocache=False):
    return http_client.name.resolve(name=ipns_id, nocache=nocache).get("Path")


def download_ipns_record(name, path="", nocache=False):
    return download(resolve_ipns_key(name, nocache=nocache), path)


def read_ipns_record(name, nocache=False):
    return read(resolve_ipns_key(name, nocache=nocache))

# Returns a list of the multiaddresses of all connected peers


def list_peer_multiaddrs():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8').strip("\n"))

    return peers

# Returns the multiaddresses of input the peer ID


def find_peer(ID: str):
    try:
        response = http_client.dht.findpeer(ID)
        if(len(response.get("Responses")[0].get("Addrs")) > 0):
            return response
    except:
        return None


# Returns the IPFS ID of the currently running IPFS node
def my_id():
    return http_client.id().get("ID")


def listen_on_port(protocol, port):
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


def forward_from_port_to_peer(protocol: str, port, peerID):
    http_client.p2p.forward("/x/" + protocol, "/ip4/127.0.0.1/tcp/" +
                            str(port), "/p2p/" + peerID)


def close_port_forwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    http_client.p2p.close(all, protocol, listenaddress, targetaddress)


def check_peer_connection(id, name=""):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in ipfs_lns.
    Paramaters:
        id: the IPFS PeerID or the ipfs_lns name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    contact = ipfs_lns.get_contact(id)
    if not contact:
        contact = ipfs_lns.add_contact(id, name)
    return contact.check_connection()


def find_providers(cid):
    """Returns a list of the IDs of the peers who provide the file
    with the given CID  (including onesself).
    E.g. to check if this computer hosts a file with a certain CID:
    def DoWeHaveFile(cid:str):
        ipfs_api.my_id() in ipfs_api.find_providers(cid)
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


class PubsubListener():
    _terminate = False
    __listening = False

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
                    with http_client.pubsub.subscribe(self.topic) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = {
                                "senderID": message["from"],
                                "data": _decode_base64_url(message["data"]),
                            }

                            _thread.start_new_thread(
                                self.eventhandler, (data,))
                else:
                    with http_client.pubsub.subscribe_old(self.topic) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = str(base64.b64decode(
                                str(message).split('\'')[7]), "utf-8")
                            _thread.start_new_thread(
                                self.eventhandler, (data,))
            except ConnectionError:
                pass
                # print(f"IPFS API Pubsub: restarting sub {self.topic}")
        self.__listening = False

    def listen(self):
        self._terminate = False
        thr = Thread(target=self._listen, args=())
        thr.start()

    def terminate(self):
        """May let one more pubsub message through"""
        self._terminate = True


def pubsub_publish(topic, data):
    """Publishes te specified data to the specified IPFS-PubSub topic.
    Parameters:
        topic: str: the name of the IPFS PubSub topic to publish to
        data: string or bytes/bytearray: either the filepath of a file whose
            content should be published to the pubsub topic,
            or the raw data to be published as a string or bytearray.
            When using an older version of IPFS < v0.11.0 however,
            only plai data as a string is accepted.
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
    to the evventhandler.
    Parameters:
        topic: str: the name of the IPFS PubSub topic to publish to
        eventhandler: function(dict): the function to be executed whenever a message is received.
                            The eventhandler parameter is a dict with the keys 'data' and 'senderID',
                            except when using an older version of IPFS < v0.11.0,
                            in which case only the message is passed as a string.
    Returns a PubsubListener object which can  be terminated with the .terminate() method (and restarted with the .listen() method)
    """
    return PubsubListener(topic, eventhandler)


def pubsub_unsubscribe(topic, eventhandler):
    index = 0
    for subscription in subscriptions:
        if(subscription[0] == topic and subscription[1] == eventhandler):
            subscription[2].terminate()
            break
        index = index + 1
    subscriptions.pop(index)    # remove the subscription from the list of subscriptions


def pubsub_peers(topic: str):
    """
    Returns the list of peers we are connected to on the specified pubsub topic
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
    data = b'u'+data
    return data


if autostart:
    if not LIBERROR:    # if all modules needed for the ipfs_http_client library were loaded
        start()
    if not started:
        from ipfs_cli import *
        if not is_daemon_running():
            run_daemon()


"""Deprecated naming of Functions:"""


def Start():
    print(colored("IPFS_API: DEPRECATED: This function (start) has been renamed to Start to accord with PEP 8 naming conventions.", "yellow"))
    return start()


def PublishToTopic(topic, data):
    print(colored("IPFS_API: DEPRECATED: This function (PublishToTopic) has been renamed to pubsub_publish to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_publish(topic, data)


def SubscribeToTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (SubscribeToTopic) has been renamed to pubsub_subscribe to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_subscribe(topic, eventhandler)


def UnsubscribeFromTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (UnsubscribeFromTopic) has been renamed to pubsub_unsubscribe to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_unsubscribe(topic, eventhandler)


def TopicPeers(topic: str):
    print(colored("IPFS_API: DEPRECATED: This function (TopicPeers) has been renamed to pubsub_peers to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_peers(topic)


def UploadFile(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (UploadFile) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Upload(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (Upload) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Publish(path: str):
    print(colored("IPFS_API: DEPRECATED: This function (Publish) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(path)


def Pin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (Pin) has been renamed to pin to accord with PEP 8 naming conventions.", "yellow"))
    return pin(cid)


def Unpin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (Unpin) has been renamed to unpin to accord with PEP 8 naming conventions.", "yellow"))
    return unpin(cid)


def Download_file(ID, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (Download_file) has been renamed to download to accord with PEP 8 naming conventions.", "yellow"))
    return download(ID, path)


def Download(cid, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (Download) has been renamed to download to accord with PEP 8 naming conventions.", "yellow"))
    return download(cid, path)


def CatFile(ID):
    print(colored("IPFS_API: DEPRECATED: This function (CatFile) has been renamed to read to accord with PEP 8 naming conventions.", "yellow"))
    return read(ID)


def CreateIPNS_Record(name: str, type: str = "rsa", size: int = 2048):
    print(colored("IPFS_API: DEPRECATED: This function (CreateIPNS_Record) has been renamed to create_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return create_ipns_record(name, type, size)


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (UpdateIPNS_RecordFromHash) has been renamed to update_ipns_record_from_hash to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record_from_hash(name, cid, ttl, lifetime)


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (UpdateIPNS_Record) has been renamed to update_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record(name, path, ttl, lifetime)


def ResolveIPNS_Key(ipns_id, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (ResolveIPNS_Key) has been renamed to resolve_ipns_key to accord with PEP 8 naming conventions.", "yellow"))
    return resolve_ipns_key(ipns_id, nocache)


def DownloadIPNS_Record(name, path="", nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (DownloadIPNS_Record) has been renamed to download_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return download_ipns_record(name, path, nocache)


def CatIPNS_Record(name, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (CatIPNS_Record) has been renamed to read_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return read_ipns_record(name, nocache)


def ListPeerMaddresses():
    print(colored("IPFS_API: DEPRECATED: This function (ListPeerMaddresses) has been renamed to list_peer_multiaddrs to accord with PEP 8 naming conventions.", "yellow"))
    return list_peer_multiaddrs()


def FindPeer(ID: str):
    print(colored("IPFS_API: DEPRECATED: This function (FindPeer) has been renamed to find_peer to accord with PEP 8 naming conventions.", "yellow"))
    return find_peer(ID)


def MyID():
    print(colored("IPFS_API: DEPRECATED: This function (MyID) has been renamed to my_id to accord with PEP 8 naming conventions.", "yellow"))
    return my_id()


def ListenOnPort(protocol, port):
    print(colored("IPFS_API: DEPRECATED: This function (ListenOnPort) has been renamed to listen_on_port to accord with PEP 8 naming conventions.", "yellow"))
    return listen_on_port(protocol, port)


def ForwardFromPortToPeer(protocol: str, port, peerID):
    print(colored("IPFS_API: DEPRECATED: This function (ForwardFromPortToPeer) has been renamed to forward_from_port_to_peer to accord with PEP 8 naming conventions.", "yellow"))
    return forward_from_port_to_peer(protocol, port, peerID)


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    print(colored("IPFS_API: DEPRECATED: This function (ClosePortForwarding) has been renamed to close_port_forwarding to accord with PEP 8 naming conventions.", "yellow"))
    return close_port_forwarding(all, protocol, listenaddress, targetaddress)


def CheckPeerConnection(id, name=""):
    print(colored("IPFS_API: DEPRECATED: This function (CheckPeerConnection) has been renamed to check_peer_connection to accord with PEP 8 naming conventions.", "yellow"))
    return check_peer_connection(id, name)


def FindProviders(cid):
    print(colored("IPFS_API: DEPRECATED: This function (FindProviders) has been renamed to find_providers to accord with PEP 8 naming conventions.", "yellow"))
    return find_providers(cid)
