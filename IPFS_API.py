# This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
# process running on the computer.
# To use it you must have IPFS running on your computer.
# This wrapper uses a custom updated version of the ipfshttpclient.


import sys
from subprocess import Popen, PIPE
import subprocess
import _thread
import os
import os.path
import threading
import base64
import ipfshttpclient2 as ipfshttpclient
from requests.exceptions import ConnectionError
# import multiprocessing
import traceback
import IPFS_LNS

print_log = False

autostart = True
started = False
http_client = ipfshttpclient.client.Client()
# List for keeping track of subscriptions to IPFS topics, so that subscriptions can be ended
subscriptions = list([])


def Start():
    try:
        global started
        ipfs = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
        started = True
        return True
    except Exception as e:
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


# Publishes the input text to specified the IPFS PubSub topic
def PublishToTopic(topic, text):
    http_client.pubsub.publish(topic, text)

# Listens to the specified IPFS PubSub topic and passes received text to the input eventhandler function


def SubscribeToTopic(topic, eventhandler):
    def Listen():
        while True:
            try:
                sub = http_client.pubsub.subscribe(topic)
                with http_client.pubsub.subscribe(topic) as sub:
                    for text in sub:
                        _thread.start_new_thread(
                            eventhandler, (str(base64.b64decode(str(text).split('\'')[7]), "utf-8"),))
            except ConnectionError as e:
                print(f"IPFS API Pubsub: restarting sub {topic}")

    #thread =  multiprocessing.Process(target = Listen, args= ())
    # thread.start()
    _thread.start_new_thread(Listen, ())
    #subscriptions.append((topic, eventhandler, thread))
    # return thread


def UnSubscribeFromTopic(topic, eventhandler):
    index = 0
    for subscription in subscriptions:
        if(subscription[0] == topic and subscription[1] == eventhandler):
            subscription[2].terminate()
            break
        index = index + 1
    subscriptions.pop(index)    # remove the subscription from the list of subscriptions


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
    data = http_client.cat(ID)
    if path != "":
        file = open(path, "wb")
        file.write(data)
        file.close()
    return data


def CatFile(ID):
    return http_client.cat(ID)


def CreateIPNS_Record(name: str):
    result = http_client.key.gen(key_name=name, type="rsa")
    print(result)
    if(type(result) == list):
        return result[-1].get("Id")
    else:
        return result.get("Id")


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    http_client.name.publish(ipfs_path=cid, key=name, ttl=ttl, lifetime=lifetime)


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    cid = PublishFile(path)
    UpdateIPNS_RecordFromHash(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def DownloadIPNS_Record(name, path="", nocache=False):
    return DownloadFile(ResolveIPNS_Key(name, nocache=nocache), path)


def ResolveIPNS_Key(ipns_id, nocache=False):
    return http_client.name.resolve(name=ipns_id, nocache=nocache).get("Path")


def CatIPNS_Record(name, nocache=False):
    ipfs_path = http_client.name.resolve(name=name, nocache=nocache).get("Path")
    return CatFile(ipfs_path)

# Returns a list of the multiaddresses of all connected peers


def ListPeerMaddresses():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8'))

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
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


listenonportTCP = ListenOnPortTCP
ListenTCP = ListenOnPortTCP
listentcp = ListenOnPortTCP


def ListenOnPort(protocol, port):
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


listenonportUDP = ListenOnPort
ListenUDP = ListenOnPort
listenudp = ListenOnPort
listenonport = ListenOnPort
Listen = ListenOnPort
listen = ListenOnPort


def ForwardFromPortToPeer(protocol: str, port, peerID):
    http_client.p2p.forward("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port), "/p2p/" + peerID)


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


if autostart:
    Start()
