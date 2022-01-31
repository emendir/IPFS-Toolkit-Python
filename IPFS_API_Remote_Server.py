import IPFS_API
# Topic Communications Terminal (BoCom)
# This class contains the machinery that receives and processes incoming requests from topic programs and calls the requested
# blockchain functions (such as CreateBlock() and ListenOnTopic()) accordingly using the provided input and returning the produced output.
# The communication between this blockchain program and the topic programs runs over the computer's local network. That means that this
# program listens to incoming communication on a certain network port and that the topic programs listen to notifications by this
# blockchain program on their own ports.
# The format of all the data communicated between this blockchain program and the topic programs is dictionaries, which are serialised by JSONPickle and encoded into bytearrays.
import zmq
import json
import traceback
import time
import socketserver
import socket
import IPFS_LNS
import ipfshttpclient2 as ipfshttpclient
http_client = ipfshttpclient.client.Client()

# the local netwok address on which this program listens to incoming requests from topic programs
request_address = ('127.0.0.1', 2610)


def ListenOnPort(request):
    """"""
    protocol, port = request["protocol"], request["port"]
    IPFS_API.ListenOnPort(protocol, port)


def MyID(request):
    return IPFS_API.MyID()


def ForwardFromPortToPeer(request):
    protocol, port, peerID = request["protocol"], request["port"], request["peerID"]
    IPFS_API.ForwardFromPortToPeer(protocol, port, peerID)


def ClosePortForwarding(request):
    all, protocol, listenaddress, targetaddress = request["all"], request[
        "protocol"], request["listenaddress"], request["targetaddress"],
    return IPFS_API.ClosePortForwarding(all, protocol, listenaddress, targetaddress)


def CheckPeerConnection(request):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in IPFS_LNS.
    Paramaters:
        id: the IPFS PeerID or the IPFS_LNS name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    id, name = request["id"], request["name"]
    return IPFS_API.CheckPeerConnection(id, name)


def RequestRouter(request):
    if(request.get("function") == "ListenOnPort"):
        return ListenOnPort(request)
    elif (request.get("function") == "MyID"):
        # print(f"GET BLOCK {request['blockchain_name']}")
        return MyID(request)
    elif(request.get("function") == "ForwardFromPortToPeer"):
        return ForwardFromPortToPeer(request)
    elif(request.get("function") == "ClosePortForwarding"):
        # print(f"GET LATEST FEW BLOCKS {request['blockchain_name']}")
        return ClosePortForwarding(request)
    elif(request["function"] == "ClosePortForwarding"):
        return ClosePortForwarding(request)
    else:
        print("BoCom: Received request that was not understood.")
        return {"message": "not understood"}


def StartListeningForRequestsZMQ():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://{request_address[0]}:{request_address[1]}")
    #port = socket.bind_to_random_port("tcp://*")

    while True:
        #  Wait for next request from client
        request = socket.recv()
        reply = RequestRouter(json.loads(request.decode()))
        socket.send(json.dumps(reply).encode())


def StartListeningForRequests():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((request_address[0], request_address[1]))
        while True:
            s.listen()
            conn, addr = s.accept()
            with conn:
                while True:
                    request = conn.recv(1024)
                    if not request:
                        print("Received null data")
                        break
                    reply = RequestRouter(json.loads(request.decode()))
                    print("Replying: ", json.dumps(reply))
                    conn.sendall(json.dumps(reply).encode())

            # s.close()


StartListeningForRequests()
