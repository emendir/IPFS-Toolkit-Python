# This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
# process running on the computer.
# To use it you must have IPFS running on your computer.
# This wrapper uses a custom updated version of the ipfshttpclient.


import shutil
import tempfile
import sys
from subprocess import Popen, PIPE
import subprocess
import _thread
import os
import os.path
import threading
# import multiprocessing
import traceback
import IPFS_LNS
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


def Start():
    try:
        global started
        from IPFS_CLI import RunCommand, ipfs_cmd
        Thread(target=RunCommand, args=[ipfs_cmd, "daemon", "--enable-pubsub-experiment"])

        http_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
        started = True
        logging.info("Started IPFS_API, connected to daemon")
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


# Publishes the input data to specified the IPFS PubSub topic
def PublishToTopic(topic, data):
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


# Listens to the specified IPFS PubSub topic and passes received data to the input eventhandler function


class PubsubListener():
    terminate = False
    __listening = False

    def __init__(self, topic, eventhandler):
        self.topic = topic
        self.eventhandler = eventhandler
        self.Listen()

    def _listen(self):
        if self.__listening:
            return
        self.__listening = True
        """blocks the calling thread"""
        while not self.terminate:
            try:
                if int(http_client.version()["Version"].split(".")[1]) >= 11:
                    with http_client.pubsub.subscribe(self.topic) as self.sub:
                        for message in self.sub:
                            if self.terminate:
                                self.__listening = False
                                return
                            data = {
                                "senderID": message["from"],
                                "data": _DecodeBase64URL(message["data"]),
                            }

                            _thread.start_new_thread(
                                self.eventhandler, (data,))
                else:
                    with http_client.pubsub.subscribe_old(self.topic) as self.sub:
                        for message in self.sub:
                            if self.terminate:
                                self.__listening = False
                                return
                            data = str(base64.b64decode(
                                str(message).split('\'')[7]), "utf-8")
                            _thread.start_new_thread(
                                self.eventhandler, (data,))
            except ConnectionError as e:
                print(f"IPFS API Pubsub: restarting sub {self.topic}")
        self.__listening = False

    def Listen(self):
        self.terminate = False
        thr = Thread(target=self._listen, args=())
        thr.start()

    def Terminate(self):
        """May let one more pubsub message through"""
        self.terminate = True


def SubscribeToTopic(topic, eventhandler):
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
    Returns a PubsubListener object which can  be terminated with the .Terminate() method (and restarted with the .Listen() method)
    """
    return PubsubListener(topic, eventhandler)


def UnSubscribeFromTopic(topic, eventhandler):
    index = 0
    for subscription in subscriptions:
        if(subscription[0] == topic and subscription[1] == eventhandler):
            subscription[2].terminate()
            break
        index = index + 1
    subscriptions.pop(index)    # remove the subscription from the list of subscriptions


def TopicPeers(topic: str):
    """
    Returns the list of peers we are connected to on the specified pubsub topic
    """
    return http_client.pubsub.peers(topic=_EncodeBase64URL(topic.encode()))["Strings"]


def UploadFile(filename: str):
    print("IPFS_API: WARNING: deprecated. Use Publish() instead.")
    return Publish(filename)


def Upload(filename: str):
    print("IPFS_API: WARNING: deprecated. Use Publish() instead.")
    return Publish(filename)


def Publish(path: str):
    """
    Upload a file or a directory to IPFS.
    Returns the Hash of the uploaded file.
    """
    result = http_client.add(path, recursive=True)
    if(type(result) == list):
        return result[-1].get("Hash")
    else:
        return result.get("Hash")
# Downloads the file with the specified ID and saves it with the specified path


def Pin(cid: str):
    http_client.pin.add(cid)


def Unpin(cid: str):
    http_client.pin.rm(cid)


def DownloadFile(ID, path=""):
    print("IPFS_API: WARNING: deprecated. Use Download() instead.")
    data = http_client.cat(ID)
    if path != "":
        file = open(path, "wb")
        file.write(data)
        file.close()
    return data


def Download(cid, path=""):
    # create temporary download directory
    tempdir = tempfile.mkdtemp()

    # download and save file/folder to temporary directory
    http_client.get(cid=cid, target=tempdir)

    # move file/folder from temporary directory to desired path
    shutil.move(os.path.join(tempdir, cid), path)

    # cleanup temporary directory
    shutil.rmtree(tempdir)


def CatFile(ID):
    return http_client.cat(ID)


def CreateIPNS_Record(name: str, type: str = "rsa", size: int = 2048):
    result = http_client.key.gen(key_name=name, type=type, size=size)
    print(result)
    if isinstance(result, list):
        return result[-1].get("Id")
    else:
        return result.get("Id")


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    http_client.name.publish(ipfs_path=cid, key=name, ttl=ttl, lifetime=lifetime)


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    cid = Publish(path)
    UpdateIPNS_RecordFromHash(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def ResolveIPNS_Key(ipns_id, nocache=False):
    return http_client.name.resolve(name=ipns_id, nocache=nocache).get("Path")


def DownloadIPNS_Record(name, path="", nocache=False):
    return Download(ResolveIPNS_Key(name, nocache=nocache), path)


def CatIPNS_Record(name, nocache=False):
    return CatFile(ResolveIPNS_Key(name, nocache=nocache))

# Returns a list of the multiaddresses of all connected peers


def ListPeerMaddresses():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8').strip("\n"))

    return peers

# Returns the multiaddresses of input the peer ID


def FindPeer(ID: str):
    try:
        response = http_client.dht.findpeer(ID)
        if(len(response.get("Responses")[0].get("Addrs")) > 0):
            return response
    except:
        return None


# Returns the IPFS ID of the currently running IPFS node
def MyID():
    return http_client.id().get("ID")


myid = MyID


def ListenOnPortTCP(protocol, port):
    print("IPFS_API: WARNING: deprecated. Use ListenOnPort() instead.")
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


listenonportTCP = ListenOnPortTCP
ListenTCP = ListenOnPortTCP
listentcp = ListenOnPortTCP


def ListenOnPort(protocol, port):
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


listenonport = ListenOnPort
Listen = ListenOnPort
listen = ListenOnPort


def ForwardFromPortToPeer(protocol: str, port, peerID):
    http_client.p2p.forward("/x/" + protocol, "/ip4/127.0.0.1/tcp/" +
                            str(port), "/p2p/" + peerID)


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    http_client.p2p.close(all, protocol, listenaddress, targetaddress)


def CheckPeerConnection(id, name=""):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in IPFS_LNS.
    Paramaters:
        id: the IPFS PeerID or the IPFS_LNS name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    contact = IPFS_LNS.GetContact(id)
    if not contact:
        contact = IPFS_LNS.AddContact(id, name)
    return contact.CheckConnection()


def FindProviders(cid):
    """Returns a list of the IDs of the peers who provide the file
    with the given CID  (including onesself).
    E.g. to check if this computer hosts a file with a certain CID:
    def DoWeHaveFile(cid:str):
        IPFS_API.MyID() in IPFS_API.FindProviders(cid)
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


def _DecodeBase64URL(data: str):
    """Performs the URL-Safe multibase decoding required by some functions (since IFPS v0.11.0) on strings"""
    if isinstance(data, bytes):
        data = data.decode()
    data = str(data)[1:].encode()
    missing_padding = len(data) % 4
    if missing_padding:
        data += b'=' * (4 - missing_padding)
    return urlsafe_b64decode(data)


def _EncodeBase64URL(data: bytearray):
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
        Start()
    if not started:
        from IPFS_CLI import *
        if not IsDaemonRunning():
            RunDaemon()
