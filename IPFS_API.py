## This is a wrapper for the ipfshttpclient module to make it easier to interact with the Interplanetary File System (IPFS)
## process running on the computer.
## To use it you must have IPFS running on your computer.
## This wrapper uses a custom updated version of the ipfshttpclient.

import sys
from subprocess import Popen, PIPE
import subprocess
import _thread
import os
import os.path
import threading
import base64
import ipfshttpclient2 as ipfshttpclient
import multiprocessing
import traceback

autostart = True

ipfs = ipfshttpclient.client.Client()
subscriptions = list([])    # List for keeping track of subscriptions to IPFS topics, so that subscriptions can be ended

def Start():
    try:
        ipfs = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
        return True
    except Exception as e:
        print("")
        print("----------------------------------------------------")
        traceback.print_exc() # printing stack trace
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
    ipfs.pubsub.publish(topic, text)

# Listens to the specified IPFS PubSub topic and passes received text to the input eventhandler function
def SubscribeToTopic(topic, eventhandler):
    def Listen():
        sub = ipfs.pubsub.subscribe(topic)
        with ipfs.pubsub.subscribe(topic) as sub:
            for text in sub:
                _thread.start_new_thread(eventhandler, (str(base64.b64decode(str(text).split('\'')[7]), "utf-8"),))
    #thread =  multiprocessing.Process(target = Listen, args= ())
    #thread.start()
    _thread.start_new_thread(Listen, ())
    #subscriptions.append((topic, eventhandler, thread))
    #return thread

def UnSubscribeFromTopic(topic, eventhandler):
    index = 0
    for subscription in subscriptions:
        if(subscription[0] == topic and subscription[1] == eventhandler):
            subscription[2].terminate()
            break
        index = index + 1
    subscriptions.pop(index)    # remove the subscription from the list of subscriptions


# publishes the input file on IPFS and returns the newly published file's ID
def PublishFile(path):
    output = ipfs.add(path)
    return str(output).split("\'")[7] # extracting the file ID from the process' output

# Downloads the file with the specified ID and saves it with the specified path
def DownloadFile(ID, path):
    data = ipfs.cat(ID)
    file = open(path, "wb")
    file.write(data)
    file.close()


# Returns a list of the multiaddresses of all connected peers
def ListPeerMaddresses():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8'))

    return peers

# Returns the multiaddresses of input the peer ID
def FindPeer(ID :str):
    try:
        response = ipfs.dht.findpeer(ID)
        if(len(response.get("Responses")[0].get("Addrs"))> 0):
            return response
    except:
        return None


# Returns the IPFS ID of the currently running IPFS node
def MyID():
    return ipfs.id().get("ID")


def ListenOnPort(protocol, port):
    ipfs.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


def ForwardFromPortToPeer(protocol, port, peerID):
    ipfs.p2p.forward("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port), "/p2p/" + peerID)

def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    ipfs.p2p.close(all, protocol, listenaddress, targetaddress)


if autostart:
    Start()
