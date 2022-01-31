# import IPFS_API
# import zmq
import socket
import json

import _thread
import time
import traceback
from datetime import datetime
import os
from inspect import signature
import appdirs

bc_term_request_address = ('127.0.0.1', 2610)


def ListenOnPort(protocol, port):
    """"""
    request = {"function": "ListenOnPort", "protocol": protocol, "port": port}
    return SendRequest(request)


def MyID():
    """"""
    request = {"function": "MyID"}
    return SendRequest(request)


def ForwardFromPortToPeer(protocol: str, port, peerID):
    """"""
    request = {"function": "ForwardFromPortToPeer",
               "protocol": protocol, "port": port, "peerID": peerID}
    return SendRequest(request)


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    """"""
    request = {"function": "ClosePortForwarding", "all": all, "protocol": protocol,
               "listenaddress": listenaddress, "targetaddress": targetaddress, }
    return SendRequest(request)


def CheckPeerConnection(id, name=""):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in IPFS_LNS.
    Paramaters:
        id: the IPFS PeerID or the IPFS_LNS name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    request = {"function": "CheckPeerConnection", "name": name}
    return SendRequest(request)


def SendRequestZMQ(request):
    import zmq

    context = zmq.Context()

    socket = context.socket(zmq.REQ)
    socket.connect(
        f"tcp://{bc_term_request_address[0]}:{bc_term_request_address[1]}")
    socket.send(json.dumps(request).encode())

    reply = socket.recv()
    return json.loads(reply.decode())


def SendRequest(request):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((bc_term_request_address[0], bc_term_request_address[1]))
        s.sendall(json.dumps(request).encode())
        reply = s.recv(1024)
        return json.loads(reply.decode())


def GetTimeStamp(date_time):
    if not date_time:
        return
    return ToB255No0s(date_time.year) + bytearray([0]) + ToB255No0s(date_time.month) + bytearray([0]) + ToB255No0s(date_time.day) + bytearray([0]) + ToB255No0s(date_time.hour) + bytearray([0]) + ToB255No0s(date_time.minute) + bytearray([0]) + ToB255No0s(date_time.second) + bytearray([0]) + ToB255No0s(date_time.microsecond) + bytearray([0])


def DecodeTimeStamp(array):
    if array[-1] != bytearray([0]):
        array += bytearray([0])
    # extracting the year, month, day, hour, minute, second, and microsecond from the inpur array, using the 0 separators as guides
    numbers = []
    while(len(array) > 0):
        number_b255 = array[0:array.index(bytearray([0]))]
        numbers.append(FromB255No0s(number_b255))
        # removing the year and the following zero  from the array
        array = array[array.index(bytearray([0])) + 1:]

    return datetime(year=numbers[0], month=numbers[1], day=numbers[2], hour=numbers[3], minute=numbers[4], second=numbers[5], microsecond=numbers[6])
# turns a base 10 integer into a base 255 integer in  the form of an array of bytes where each byte represents a digit, and where no byte has the value 0


def ToB255No0s(number):
    array = bytearray([])
    while(number > 0):
        # modulus + 1 in order to get a range of possible values from 1-256 instead of 0-255
        array.insert(0, int(number % 255 + 1))
        number -= number % 255
        number = number / 255
    return array


def FromB255No0s(array):
    number = 0
    order = 1
    # for loop backwards through th ebytes in array
    i = len(array) - 1  # th eindex of the last byte in the array
    while(i >= 0):
        # byte - 1 to change the range from 1-266 to 0-255
        number = number + (array[i] - 1) * order
        order = order * 255
        i = i - 1
    return number

# encoding bytearrays into strings and vice versa to work with JSON encoding


def StringToBytes(string):
    byts = bytearray([])
    while(len(string) > 0):
        byts.append(int(string[0:3]))
        string = string[3:]
    return bytearray(byts)


def BytesToString(bytes):
    string = ""
    for byte in bytes:
        stri = str(byte)
        while(len(stri) < 3):
            stri = "0" + stri
        string = string + stri
    return string
