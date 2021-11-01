# This is a module that enables the user to transmit and receive transmissions of data over the Interplanetary File System's P2P network (libp2p).
# To use it you must have IPFS running on your computer.

# This module is based on a modification of NetTerm that uses TCP for sending sockets and UDP for receiving sockets.
# NetTerm is originally made to use UDP communication.
# This module is therefore probably less transmitting data, and may not be as reliable as the UDP version.

# This module was rather hurridly put together and not all the comments will be accurate.
# It therefore still needs to be polished off.
# It's main functionality (transmitting data over the IPFS Network have been properly tested, though)

# Configure IPFS to enable all this:
# ipfs config --json Experimental.Libp2pStreamMounting true

# TODO:
# douoble check termination of Listeners and ipfs listening connections
# check if delay periods in Transmission are still necessary now that listener sockets are UDP
# Have TransmitData return success when called wth await_finish=true
# Error handling for conversations and FileTransmission
# Close conversations

import socket
import threading
from threading import Thread
import _thread
from datetime import datetime
import time
import traceback
import os
import inspect
from inspect import signature

from IPFS_API import *
import IPFS_API
IPFS_API.Start()


# -------------- Settings ---------------------------------------------------------------------------------------------------
print_log = False  # whether or not to print debug in output terminal
print_log_connections = True
print_log_transmissions = True
print_log_conversations = False
print_log_files = False

if not print_log:
    print_log_connections = False
    print_log_transmissions = False
    print_log_conversations = False
    print_log_files = False

delaymodifier = 3

delay_1 = 0.06*delaymodifier
delay_2 = 0.1*delaymodifier

resend_timeout_sec = 1
close_timeout_sec = 100

def_buffer_size = 4096  # the communication buffer size
# the size of the chunks into which files should be split before transmission
def_block_size = 1048576

free_sending_ports = [x for x in range(20001, 20500)]

# -------------- User Functions ----------------------------------------------------------------------------------------------
# Transmits a bytearray of any length to the specified host.
# Returns a transmitter object so that the status of the transmission can be monitored


def TransmitData(data, peerID, listener_name, buffer_size=def_buffer_size, await_finish=False):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified network address.

    Usage:
        transmitter = Send("data to transmit".encode("utf-8"), "Qm123456789", "applicationNo2", 2048)    # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)

    Returns:
        Transmitter transmitter: the object that contains all the machinery used to transmit the data to the receiver, from which the transmission status will in the future be able to get called from
    """
    if IPFS_API.FindPeer(peerID):
        return Transmitter(data, peerID, listener_name, buffer_size, await_finish)
    else:
        if print_log:
            print("Could not find the specified peer on the IPFS network.")


def TransmitDataAwait(data, peerID, listener_name, buffer_size=def_buffer_size):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified network address.

    Usage:
        transmitter = Send("data to transmit".encode("utf-8"), "Qm123456789", "applicationNo2", 2048)    # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)

    Returns:
        Transmitter transmitter: the object that contains all the machinery used to transmit the data to the receiver, from which the transmission status will in the future be able to get called from
    """
    if IPFS_API.FindPeer(peerID):

        t = Transmitter(data, peerID, listener_name, buffer_size, True)
    else:
        if print_log:
            print("Could not find the specified peer on the IPFS network.")

# Sets itself up to receive data transmissions, transmitted by the sender using the TransmitData function.
# Returns the Listener object so that receiving the data transmissions can be stopped by calling listener.Terminate().


def ListenForTransmissions(listener_name, eventhandler):
    """
    Listens for incoming transmission requests (senders requesting to transmit data to us) and sets up the machinery needed to receive those transmissions.

    Usage:
        def OnReceive(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        # listening with a Listener-Name of "applicationNo2"
        listener = ReceiveTransmissions("applicationNo2", OnReceive)

        # When we no longer want to receive any transmissions:
        listener.Terminate()

    Parameters:
        string listener_name: the name of this TransmissionListener (chosen by user, allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        function(bytearray data, string peerID) eventhandler: the function that should be called when a transmission of data is received
    """
    # This function itself is called to process the transmission request buffer sent by the transmission sender.
    def ReceiveTransmissionRequests(data, addr):
        if print_log_transmissions:
            print(listener_name + ": processing transmission request...")
        # decoding the transission request buffer
        try:
            # Performing buffer integrity check
            integrity_byte = data[0]
            data = data[1:]
            sum = 0
            for byte in data:
                sum += byte
                if sum > 65000:  # if the sum is reaching the upper limit of an unsigned 16-bit integer
                    sum = sum % 256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
            # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
            if sum % 256 != integrity_byte:
                if print_log:
                    print(
                        listener_name + ": Received a buffer with a non-matching integrity buffer")
                return

            index = data.index(bytearray([255]))
            peerID = data[0:index].decode()
            data = data[index + 1:]

            index = data.index(bytearray([0]))
            sender_port = FromB255No0s(data[0:index])
            data = data[index + 1:]

            buffer_size = FromB255No0s(data)

            return TransmissionListener(peerID, sender_port, buffer_size, eventhandler)

        except Exception as e:
            print("")
            print(
                listener_name + ": Exception in NetTerm.ReceiveTransmissions.ReceiveTransmissionRequests()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print(listener_name + ": Could not decode transmission request.")

    request_listener = Listener(
        ReceiveTransmissionRequests, 0, def_buffer_size)
    port = request_listener.port
    CreateListeningConnection(listener_name, port)

    if print_log_transmissions:
        print(listener_name
              + ": Listening for transmission requests as " + listener_name)

    return request_listener


def StartConversation(conversation_name, peerID, others_req_listener, eventhandler):
    """Starts a conversation object with which peers can send data transmissions to each other.
    Code execution continues before the other peer joins the conversation.
    Sends a conversation request to the other peer's conversation request listener which the other peer must accept (joining the conversation) in order to start the conversation.
    Usage:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = StartConversation("test", "QmHash", "conv listener", OnReceive)
        time.sleep(5)   # giving time for the connection to set up
        conversation.Say("Hello there!".encode())

        # the other peer must have a conversation listener named "conv listener" running, e.g. via:
        ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function

    Parameters:
        1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
        2. peerID: the IPFS peer ID of the node to communicate with
        3. others_req_listener: the name of the ther peer's conversation listener object
    """
    conv = Conversation()
    conv.Start(conversation_name, peerID, others_req_listener, eventhandler)
    return conv


def StartConversationAwait(conversation_name, peerID, others_req_listener, eventhandler):
    """Starts a conversation object with which peers can send data transmissions to each other.
    Waits (Blocks the calling thread) until the target peer has joined the conversation.
    Sends a conversation request to the other peer's conversation request listener which the other peer must accept (joining the conversation) in order to start the conversation.

    Usage:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = StartConversation("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        # the other peer must have a conversation listener named "conv listener" running, e.g. via:
        ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function

    Parameters:
        1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
        2. peerID: the IPFS peer ID of the node to communicate with
        3. others_req_listener: the name of the ther peer's conversation listener object
    """
    conv = Conversation()
    conv.StartAwait(conversation_name, peerID,
                    others_req_listener, eventhandler)
    return conv


def ListenForConversations(conv_name, eventhandler):
    return ConversationListener(conv_name, eventhandler)


class Conversation:
    """
    Communication object which allows peers to easily transmit data to eacch other.
    Usage example:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = Conversation()
        conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        # the other peer must have a conversation listener named "conv listener" running, e.g. via:
        ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function

    Methods:
        Start: start a conversation with another peer, continuing code execution without waiting for the other peer to join.
        StartAwait: start a conversation with another peer, waiting (blocking the calling thread) until the other peer to join.
            # Note: Start and StartAwait send a conversation request to the other peer's conversation request listener which the other peer must accept (joining the conversation) in order to start the conversation.
        Join: join a conversation which another peer started. Used by a conversation listener. See ListenForConversations for usage.
    """
    conversation_started = False

    def Start(self, conversation_name, peerID, others_req_listener, eventhandler):
        """Starts a conversation object with which peers can send data transmissions to each other.
        Code execution continues before the other peer joins the conversation
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.Start("test", "QmHash", "conv listener", OnReceive)
            time.sleep(5)   # giving time for the connection to set up
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function

        Parameters:
            1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID: the IPFS peer ID of the node to communicate with
            3. others_req_listener: the name of the ther peer's conversation listener object
        """
        if(print_log_conversations):
            print(conversation_name + ": Starting conversation")
        self.conversation_name = conversation_name

        def AwaitResponse(conversation, data):
            info = SplitBy255(data)
            if info[0] == bytearray("I'm listening".encode('utf-8')):
                self.others_conv_listener = info[1].decode('utf-8')
                self.hear_eventhandler = eventhandler
                self.conversation_started = True
                if print_log_conversations:
                    print(conversation_name + ": conversation started")
        self.hear_eventhandler = AwaitResponse
        self.peerID = peerID
        if print_log_conversations:
            print(conversation_name + ": about to start conversation")
        self.listener = ListenForTransmissions(conversation_name, self.Hear)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        TransmitData(data, peerID, others_req_listener)

    def StartAwait(self, conversation_name, peerID, others_req_listener, eventhandler):
        """Starts a conversation object with which peers can send data transmissions to each other.
        Waits (Blocks the calling thread) until the target peer has joined the conversation.
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function

        Parameters:
            1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID: the IPFS peer ID of the node to communicate with
            3. others_req_listener: the name of the ther peer's conversation listener object
        """
        self.Start(conversation_name, peerID,
                   others_req_listener, eventhandler)
        while not self.conversation_started:
            time.sleep(0.1)

    def Join(self, conversation_name, peerID, others_conv_listener, eventhandler):
        """Joins a conversation which another peer started. Used by a conversation listener. See ListenForConversations for usage."""
        self.conversation_name = conversation_name
        if print_log_conversations:
            print(conversation_name + ": Joining conversation "
                  + others_conv_listener)
        self.hear_eventhandler = eventhandler
        self.listener = ListenForTransmissions(conversation_name, self.Hear)
        self.others_conv_listener = others_conv_listener
        self.peerID = peerID
        data = bytearray("I'm listening".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        TransmitData(data, peerID, others_conv_listener)
        self.conversation_started = True

    def Hear(self, data, peerID, arg3=""):
        """
        Receives data from the conversation and forwards it to the user's eventhandler
        """
        if len(signature(self.hear_eventhandler).parameters) == 2:    # if the eventhandler has 2 parameters
            self.hear_eventhandler(self, data)
        else:
            self.hear_eventhandler(self, data, arg3)

    def Say(self, data, buffer_size=def_buffer_size, await_finish=False):
        """Transmits data of any length to the other peer.
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            ListenForConversations("conv listener", OnReceive)  # forwards communication from any conversation to the OnReceive function
        """
        if not self.conversation_started:
            if print_log:
                print("Wanted to say something but conversation was not yet started")
                return False
        TransmitData(data, self.peerID, self.others_conv_listener,
                     buffer_size, await_finish)
        return True

    def Close(self):
        self.listener.Terminate()
        self = None


class ConversationListener:
    def __init__(self, listener_name, eventhandler):

        if(print_log_conversations):
            print("Listening for conversations as " + listener_name)
        self.eventhandler = eventhandler
        self.listener = ListenForTransmissions(
            listener_name, self.OnRequestReceived)

    def OnRequestReceived(self, data, peerID):
        if print_log:
            print("Received Transmission Request")
        info = SplitBy255(data)
        if info[0] == bytearray("I want to start a conversation".encode('utf-8')):
            if print_log:
                print("starting conversation...")
            conversation_name = info[1].decode('utf-8')
            self.eventhandler(conversation_name, peerID)


def TransmitFile(filepath, peerID, others_req_listener, metadata=bytearray(), block_size=def_block_size, buffer_size=def_buffer_size):
    """Transmits the given file to the specified peer
    Usage:
        ft = IPFS.FileTransmitter("text.txt", "QMHash", "filelistener", "testmeadata".encode())
    Paramaters:
        string filepath: the path of the file to transmit
        peerID: the IPFS ID of the computer to send the file to
    """
    return FileTransmitter(filepath, peerID, others_req_listener, metadata, block_size, buffer_size)


class FileTransmitter:
    def __init__(self, filepath, peerID, others_req_listener, metadata=bytearray(), block_size=def_block_size, buffer_size=def_buffer_size):
        self.filesize = os.path.getsize(filepath)
        self.filename = os.path.basename(filepath)
        self.filepath = filepath
        self.block_size = block_size
        self.conversation = Conversation()
        conv_name = self.filename + "_conv"
        self.conversation.StartAwait(
            conv_name, peerID, others_req_listener, self.Hear)
        self.conversation.Say(
            ToB255No0s(self.filesize) + bytearray([255])
            + bytearray(self.filename.encode()) + bytearray([255]) + metadata)
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": Sent transmission request")

    def StartTransmission(self):
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": starting transmmission")
        position = 0
        with open(self.filepath, "rb") as reader:
            while position < self.filesize:
                blocksize = self.filesize - position
                if blocksize > self.block_size:
                    blocksize = self.block_size
                data = reader.read(blocksize)
                position += len(data)
                print("FileTransmission: " + self.filename
                      + ": sending data " + str(position) + "/" + str(self.filesize))
                self.conversation.Say(
                    data, buffer_size=10000, await_finish=True)
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": finished file transmission")

    def Hear(self, conv, data):
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": received response from receiver")
        info = SplitBy255(data)
        if info[0].decode('utf-8') == "ready":
            self.StartTransmission()


class FileTransmissionReceiver:
    transmission_started = False

    def Setup(self, conversation, eventhandler, dir="."):
        if print_log_files:
            print("FileReception: "
                  + ": Preparing to receive file")

        self.eventhandler = eventhandler

        self.conv = conversation
        self.dir = dir
        if print_log_files:
            print("FileReception: "
                  + ": responded to sender, ready to receive")

    def OnDataReceived(self, conv, data):
        if not self.transmission_started:
            try:
                filesize, filename, metadata = SplitBy255(data)
                self.filesize = FromB255No0s(filesize)
                self.filename = filename.decode('utf-8')
                self.metadata = metadata
                self.writer = open(os.path.join(self.dir, self.filename), "wb")
                self.transmission_started = True
                self.conv.Say("ready".encode())
                self.writtenbytes = 0
                if print_log_files:
                    print("FileReception: " + self.filename
                          + ": ready to receive file")
                if(self.filesize == 0):
                    self.Finish()
            except:
                if print_log:
                    print("Received unreadable data on FileTransmissionListener ")
                    traceback.print_exc()

        else:
            self.writer.write(data)
            self.writtenbytes += len(data)

            if print_log_files:
                print("FileTransmission: " + self.filename
                      + ": received data " + str(self.writtenbytes) + "/" + str(self.filesize))

            if self.writtenbytes == self.filesize:
                self.Finish()
            elif self.writtenbytes > self.filesize:
                self.writer.close()
                if print_log:
                    print("something weird happened, filesize is larger than expected")

    def Finish(self):
        self.writer.close()
        if print_log:
            print("FileReception: " + self.filename
                  + ": Transmission finished.")
        if signature(self.eventhandler).parameters.get("metadata") != None:
            self.eventhandler(self.conv.peerID, os.path.join(
                self.dir, self.filename), self.metadata)
        else:
            self.eventhandler(self.conv.peerID, os.path.join(
                self.dir, self.filename))


def ListenForFileTransmissions(listener_name, eventhandler, dir="."):
    def RequestHandler(conv_name, peerID):
        ft = FileTransmissionReceiver()
        conv = Conversation()
        ft.Setup(conv, eventhandler, dir)
        conv.Join(conv_name, peerID, conv_name, ft.OnDataReceived)

        return

        filesize, filename, conv_name = SplitBy255(data)
        file_size = FromB255No0s(filesize)
        filename = filename.decode('utf-8')
        conv_name = conv_name.decode('utf-8')
        FileTransmissionReceiver(
            peerID, conv_name, filename, file_size, eventhandler)

        return
        try:
            filesize, filename, conv_name = SplitBy255(data)
            file_size = FromB255No0s(filesize)
            filename = filename.decode('utf-8')
            conv_name = conv_name.decode('utf-8')
            FileTransmissionReceiver(
                peerID, conv_name, filename, file_size, eventhandler)
        except:
            if print_log:
                print(
                    "Received unreadable data on FileTransmissionListener " + listener_name)
    return ConversationListener(listener_name, RequestHandler)


# ----------IPFS Technicalitites-------------------------------------------
connections_send = list()
connections_listen = list()


def CreateSendingConnection(peerID: str, protocol: str, port=None):
    IPFS_API.ClosePortForwarding(
        targetaddress="/p2p/" + peerID, protocol="/x/" + protocol)

    if port == None:
        for prt in free_sending_ports:
            try:
                ForwardFromPortToPeer(protocol, prt, peerID)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('127.0.0.1', prt))
                return s
            except:
                pass
        print("failed to find free port for sending connection")
    else:
        ForwardFromPortToPeer(protocol, port, peerID)
        print("PORT SPECIFIED")


def CreateListeningConnectionTCP(protocol, port):
    try:
        ListenOnPort(protocol, port)
        if print_log_connections:
            print(f"listening as \"{protocol}\" on {port}")
    except Exception as e:
        IPFS_API.ClosePortForwarding(
            listenaddress=f"/ip4/127.0.0.1/tcp/{port}")
        IPFS_API.ClosePortForwarding(protocol=f"/x/{protocol}")
        try:
            ListenOnPort(protocol, port)
        except:
            print(f"listening as \"{protocol}\" on {port}")
            print("")
            print(
                "Exception in IPFS_DataTransmission.CreateListeningConnectionTCP()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("Error registering Listening connection to IPFS")
            print("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))
    connections_listen.append((protocol, port))
    return port


def CreateListeningConnection(protocol, port):
    try:
        ListenOnPort(protocol, port)
        if print_log_connections:
            print(f"listening fas \"{protocol}\" on {port}")
    except Exception as e:
        IPFS_API.ClosePortForwarding(
            listenaddress=f"/ip4/127.0.0.1/udp/{port}")
        IPFS_API.ClosePortForwarding(protocol=f"/x/{protocol}")
        try:
            time.sleep(0.1)
            ListenOnPort(protocol, port)
        except:
            print(f"listening as \"{protocol}\" on {port}")
            print("")
            print(
                "Exception in IPFS_DataTransmission.CreateListeningConnection()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("Error registering listening connection to IPFS")
            print("/x/" + protocol, "/ip4/127.0.0.1/udp/" + str(port))
            print(protocol, port)
    connections_listen.append((protocol, port))
    return port


def CloseSendingConnection(peerID, protocol):
    IPFS_API.ClosePortForwarding(
        targetaddress="/p2p/" + peerID, protocol=f"/x/{protocol}")


def CloseListeningConnection(protocol, port):
    IPFS_API.ClosePortForwarding(
        protocol=f"/x/{protocol}", targetaddress=f"/ip4/127.0.0.1/udp/{port}")


def ListenToBuffersOnPort(eventhandler, port=0, buffer_size=def_buffer_size, monitoring_interval=2, status_eventhandler=None):
    return Listener(eventhandler, port, buffer_size, monitoring_interval, status_eventhandler)


def ListenToBuffers(eventhandler, proto, buffer_size=def_buffer_size, monitoring_interval=2, status_eventhandler=None):
    listener = Listener(eventhandler, 0, buffer_size,
                        monitoring_interval, status_eventhandler)
    CreateListeningConnection(proto, listener.port)
    return listener


def SendBufferToPort(buffer, addr, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(buffer, (addr, port))


class BufferSender():

    def __init__(self, peerID, proto):
        self.peerID = peerID
        self.proto = proto
        self.sock = CreateSendingConnection(peerID, proto)

    def SendBuffer(self, data):
        try:
            self.sock.send(data)
        except:
            self.sock = CreateSendingConnection(self.peerID, self.proto)
            self.sock.send(data)


class ListenerTCP(threading.Thread):
    """
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None
    last_time_recv = datetime.utcnow()

    def __init__(self, eventhandler, port=0, buffer_size=def_buffer_size, monitoring_interval=2, status_eventhandler=None):
        threading.Thread.__init__(self)
        self.port = port
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]

        if status_eventhandler != None:
            self.status_eventhandler = status_eventhandler
            self.monitoring_interval = monitoring_interval
            self.last_time_recv = datetime.utcnow()
            self.status_monitor_thread = _thread.start_new_thread(
                self.StatusMonitor, ())

        self.start()

        if print_log_connections:
            print("Created listener.")

    def run(self):
        self.sock.listen(1)
        conn, ip_addr = self.sock.accept()

        while True:
            data = conn.recv(self.buffer_size)
            self.last_time_recv = datetime.utcnow()
            if(self.terminate == True):
                if print_log_connections:
                    print("listener terminated")
                break
            if not data:
                if print_log_connections:
                    print("received null data")
                # break
            if len(data) > 0:
                ev = Thread(target=self.eventhandler, args=(data, ip_addr))
                ev.start()

        conn.close()
        self.sock.close()
        CloseListeningConnection(str(self.port), self.port)
        if print_log_connections:
            print("Closed listener.")

    def StatusMonitor(self):
        while(True):
            if self.terminate:
                break
            time.sleep(self.monitoring_interval)
            if(datetime.utcnow() - self.last_time_recv).total_seconds() > self.monitoring_interval:
                self.status_eventhandler(
                    (datetime.utcnow() - self.last_time_recv).total_seconds())

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def Terminate(self):
        if print_log_connections:
            print("terminating listener")
        self.terminate = True   # marking the terminate flag as true
        self.sock.close()
        # SendBufferToPort(bytearray([0]),"",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop


class Listener2TCP(threading.Thread):
    """
    Listener for TransmissionRequests
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None

    def __init__(self, eventhandler, port=0, buffer_size=def_buffer_size):
        threading.Thread.__init__(self)
        self.port = port
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]
        self.start()

        if print_log_connections:
            print("Created listener.")

    def run(self):
        while True:
            self.sock.listen(1)
            conn, ip_addr = self.sock.accept()

            data = conn.recv(self.buffer_size)
            # ev =  multiprocessing.Process(target = eventhandler, args = (data, peerID))
            # ev.start()
            if(self.terminate == True):
                if print_log_connections:
                    print("listener terminated")
                break
            if not data:
                if print_log_connections:
                    print("received null data")
                # break
            if print_log_connections:
                print("Received data")
            if len(data) > 0:
                ev = Thread(target=self.eventhandler, args=(data, ip_addr))
                ev.start()
        conn.close()

        #_thread.start_new_thread(eventhandler, (data, peerID))
        self.sock.close()
        if print_log_connections:
            print("Closed listener.")

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def Terminate(self):
        self.terminate = True   # marking the terminate flag as true
        # SendBufferToPort(bytearray([0]),"",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop


class Listener(threading.Thread):
    """
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None
    last_time_recv = datetime.utcnow()

    def __init__(self, eventhandler, port=0, buffer_size=def_buffer_size, monitoring_interval=2, status_eventhandler=None):
        threading.Thread.__init__(self)
        self.port = port
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]

        if status_eventhandler != None:
            self.status_eventhandler = status_eventhandler
            self.monitoring_interval = monitoring_interval
            self.last_time_recv = datetime.utcnow()
            self.status_monitor_thread = _thread.start_new_thread(
                self.StatusMonitor, ())

        self.start()

        if print_log_connections:
            print("Created listener.")

    def run(self):

        while True:
            data, ip_addr = self.sock.recvfrom(self.buffer_size)
            self.last_time_recv = datetime.utcnow()
            if(self.terminate == True):
                if print_log_connections:
                    print("listener terminated")
                break
            if not data:
                if print_log_connections:
                    print("received null data")
                # break
            if len(data) > 0:
                if print_log_connections:
                    print("received buffer")
                ev = Thread(target=self.eventhandler, args=(data, ip_addr))
                ev.start()
            else:
                if print_log_connections:
                    print("received 0-length buffer")

        self.sock.close()
        CloseListeningConnection(str(self.port), self.port)
        if print_log_connections:
            print("Closed listener.")

    def StatusMonitor(self):
        while(True):
            if self.terminate:
                break
            time.sleep(self.monitoring_interval)
            if(datetime.utcnow() - self.last_time_recv).total_seconds() > self.monitoring_interval:
                self.status_eventhandler(
                    (datetime.utcnow() - self.last_time_recv).total_seconds())

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def Terminate(self):
        if print_log_connections:
            print("terminating listener")
        self.terminate = True   # marking the terminate flag as true
        # self.sock.close()
        # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop
        SendBufferToPort(bytearray([0]), "127.0.0.1", self.port)


class Listener2(threading.Thread):
    """
    Listener for TransmissionRequests
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None

    def __init__(self, eventhandler, port=0, buffer_size=def_buffer_size):
        threading.Thread.__init__(self)
        self.port = port
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]
        self.start()

        if print_log_connections:
            print("Created listener.")

    def run(self):
        while True:
            data, ip_addr = self.sock.recvfrom(self.buffer_size)
            # ev =  multiprocessing.Process(target = eventhandler, args = (data, peerID))
            # ev.start()
            if(self.terminate == True):
                if print_log_connections:
                    print("listener terminated")
                break
            if not data:
                print(data)
                if print_log_connections:
                    print("received null data")
                # break
            if print_log_connections:
                print("Received data")
            if len(data) > 0:
                ev = Thread(target=self.eventhandler, args=(data, ip_addr))
                ev.start()

        #_thread.start_new_thread(eventhandler, (data, peerID))
        self.sock.close()
        if print_log_connections:
            print("Closed listener.")

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def Terminate(self):
        self.terminate = True   # marking the terminate flag as true
        # self.sock.close()
        # SendBufferToPort(bytearray([0]),"127.0.0.1",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop


class Transmitter:
    """
    Contains all the machinery needed for transmitting data in the form of a bytearray of any length to a network address.
    It works by dividing the data into buffers and sending those buffers to the receiver, who must have a TransmissionListener object running and listening on that address.
    This system is immune to the buffers getting muddled up in their order or getting lost in cyberspace on their way to the receiver.

    Usage:
        transmitter = Transmitter("data to transmit".encode("utf-8"), "127.0.0.1", 8888, 2048)    # transmits "data to transmit" to the computer 127.0.0.1:8888 at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IP address of [the recipient computer to send the data to]
        int port: the port on the recipient computer to send the data to (on which the TransmissionListener is listening for transmission requests)
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)

    """

    data = ""
    peerID = ""
    buffer_size = 1024

    their_port = None

    listener = None
    our_port = 0
    transmission_started = False

    sent_buffers = list()   # list(buffer, buffer_No)

    transmission_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __init__(self, data, peerID, req_lis_name, buffer_size=def_buffer_size, await_finish=False):
        self.data = data
        self.peerID = peerID
        self.req_lis_name = req_lis_name

        self.buffer_size = buffer_size
        if buffer_size < 23:
            buffer_size = 23

        self.listener = ListenToBuffersOnPort(
            self.TransmissionReplyListener, status_eventhandler=self.NoCommunication)

        self.our_port = self.listener.port
        CreateListeningConnection(str(self.our_port), self.our_port)

        # self.listener, self.our_port = ListenToBuffersOnPort(0, self.TransmissionReplyListener)

        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        self.SendTransmissionRequest()
        if await_finish:
            self.listener.join()

    def SendTransmissionRequest(self):
        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock = CreateSendingConnection(self.peerID, self.req_lis_name)
        port = sock.getsockname()[1]
        #sock.connect(("127.0.0.1", port))
        sock.send(AddIntegrityByteToBuffer(IPFS_API.MyID().encode(
        ) + bytearray([255]) + ToB255No0s(self.our_port) + bytearray([0]) + ToB255No0s(self.buffer_size)))
        sock.close()
        if print_log_transmissions:
            print(str(self.our_port)
                  + ": Sent transmission request to " + str(self.req_lis_name))

    def SendBufferToPort(self, buffer):
        # Adding an integrity byte that equals the sum of all the bytes in the buffer modulus 256
        # to be able to detect data corruption:
        try:
            self.transmission_socket.send(AddIntegrityByteToBuffer(buffer))
            return True
        except:
            if print_log:
                print(str(self.our_port) + ": Communication to receiver at "
                      + str(self.their_port) + " broken down.")
            self.FinishedTransmission(False)
            return False

    # transmits the self.data as a series of buffers
    def SetupSendingConnection(self, peerID, protocol, sock):
        sock = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock = CreateSendingConnection(peerID, str(protocol))
            port = sock.getsockname()[1]
            return sock

        except:
            CloseSendingConnection(peerID, str(protocol))
            if print_log:
                print("connecting to port " + str(port)
                      + " failed.")

    def Transmit(self):

        if print_log_transmissions:
            print(str(self.our_port) + ": Transmission started to",
                  str(self.their_port))

        self.transmission_socket = self.SetupSendingConnection(
            self.peerID, self.their_port, self.transmission_socket)
        #self.transmission_socket.connect(("127.0.0.1", 0))
        #CreateSendingConnection(self.peerID, str(self.their_port), self.transmission_socket.port)
        position = 0
        buffer_No = 0
        time.sleep(delay_2)
        while position < len(self.data):
            buffer_metadata = ToB255No0s(buffer_No) + bytearray([0])

            # -1 to make space for the integrity buffer that gets added by the SendBufferToPort function
            buffer_content = self.data[position: position
                                       + (self.buffer_size - len(buffer_metadata) - 1)]
            position += (self.buffer_size - len(buffer_metadata) - 1)

            buffer = buffer_metadata + buffer_content
            if not self.SendBufferToPort(buffer):
                return   # aborting transmission if communication breaks down
            # adding the buffer to the list of sent buffers, just in case we have to resend it
            self.sent_buffers.append((buffer_No, buffer))
            buffer_No += 1
            time.sleep(delay_1)

        time.sleep(delay_2)
        # sending last buffer saying transmission is finished
        # if sending the buffer succeeds
        if self.SendBufferToPort("finished transmission".encode("utf-8")):
            # adding the buffer to the list of sent buffers, just in case we have to resend it
            self.sent_buffers.append(
                (buffer_No, "finished transmission".encode("utf-8")))
            if print_log_transmissions:
                print(str(self.our_port)
                      + ": sent all data to transmit to " + str(self.their_port))

    def WaitToStartTransmission(self, data):
        if print_log_transmissions:
            print(str(self.our_port) + ": Waiting to start transmission "
                  + str(self.their_port) + ", received buffer...")

        # decoding the transission request buffer
        try:
            index = data.index(bytearray([0]))
            self.their_port = FromB255No0s(data[0:index])
            data = data[index + 1:]

            content = data.decode("utf-8")
        except Exception as e:
            print("")
            print(str(self.our_port)
                  + ": Exception in NetTerm.Transmission.WaitToStartTransmission()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print(str(self.our_port) + ": could not decode buffer")
            return

        if content == "start transmission":
            self.transmission_started = True

            self.Transmit()
        else:
            if print_log:
                print(str(self.our_port)
                      + ": buffer wasn't a transmission start confirmation")
            if print_log:
                print(content)

    def ProcessConfirmationBuffer(self, data):
        if(data == "finished transmission".encode("utf-8")):
            if print_log_transmissions:
                print(str(self.our_port)
                      + ": Listener finished receiving transmission.")
            self.FinishedTransmission()
            return

        index = data.index(bytearray([0]))
        buffer_No = FromB255No0s(data[0:index])
        data = data[index + 1:]

        if(data) == "conf".encode("utf-8"):
            # remving buffer from self.sent_buffers
            index = 0
            found = False
            for buffer in self.sent_buffers:
                if buffer[0] == buffer_No:
                    found = True
                    break
                index += 1
            if found == True:
                self.sent_buffers.pop(index)
                if print_log_transmissions:
                    print(
                        str(self.our_port) + ": received confirmation buffer and removed buffer from list", buffer_No)

                # if there are older unconfirmed buffers, resend those
                if(False and index > 0):
                    for i in range(index):
                        self.SendBufferToPort(self.sent_buffers[i][1])
                        if print_log_transmissions:
                            print(str(self.our_port) + ": Resent buffer",
                                  self.sent_buffers[i][0])
            else:
                if print_log:
                    print(
                        str(self.our_port) + ": received confirmation buffer but could not find buffer in list", buffer_No)
        elif(data == "resend".encode("utf-8")):
            for buffer in self.sent_buffers:
                if buffer[0] == buffer_No:
                    self.SendBufferToPort(buffer[1])
                    if print_log_transmissions:
                        print(str(self.our_port)
                              + ": Resent buffer", buffer[0])
                    return
            if print_log:
                print(str(self.our_port)
                      + ": Could not find the buffer which was requested to be resent.")

        else:
            if print_log:
                print(data.decode("utf-8"))
                print(str(self.our_port)
                      + ": config buffer with unexpected format")
                print(data)

    def TransmissionReplyListener(self, data, peerID):
        # Performing buffer integrity check
        integrity_byte = data[0]
        data = data[1:]
        sum = 0
        for byte in data:
            sum += byte
            if sum > 65000:  # if the sum is reaching the upper limit of an unsigned 16-bit integer
                sum = sum % 256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
        # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
        if sum % 256 != integrity_byte:
            if print_log:
                print(data)
                print(str(self.our_port)
                      + ": Received a buffer with a non-matching integrity buffer")
            return

        if self.transmission_started:
            self.ProcessConfirmationBuffer(data)
        else:
            self.WaitToStartTransmission(data)

    def NoCommunication(self, time_since_last):
        if print_log_transmissions:
            print(str(self.our_port) + ": NO COMMUNICATION " + str(time_since_last))
        if(time_since_last > close_timeout_sec):
            print(str(self.our_port)
                  + ": Aborting data transmission due to no response from receiver.")
            self.FinishedTransmission(False)
        elif(time_since_last > resend_timeout_sec):
            if self.transmission_started:
                if print_log_transmissions:
                    print(str(self.our_port)
                          + ": Resending all stored buffers due to no response from receiver.")
                for buffer in self.sent_buffers:
                    self.SendBufferToPort(buffer[1])
            else:
                if print_log_transmissions:
                    print(str(self.our_port)
                          + ": Resending transmission request.")
                self.SendTransmissionRequest()

    def FinishedTransmission(self, succeeded=True):
        self.listener.Terminate()
        self.transmission_socket.close()
        CloseListeningConnection(str(self.our_port), self.our_port)
        CloseSendingConnection(self.peerID, self.req_lis_name)
        CloseSendingConnection(self.peerID, str(self.their_port))
        if print_log_transmissions:
            if succeeded:
                print(str(self.our_port) + ": Finished transmission.")
            else:
                print(str(self.our_port) + ": Transmission failed.")


# Contains all the machinery needed for receiving a transmission.
class TransmissionListener:
    """
    Contains all the machinery needed for receiving a transmission of data in the form of a bytearray of any length over a network.
    It receives the data divided into buffers by the sender, who has a Transmitter object running and transmitting the data to us.
    This system is immune to the buffers getting muddled up in their order or getting lost in cyberspace on their way to the receiver.

    Usage:
        This class must be used within a larger piece of machinery for receiving transmissions. This class only handles the reception
        of a single transmission after the transmitter has alsready sent the transmission request.
        That transmission request (a single buffer) contains encoded in it the port and buffer size needed to create a TransmissionListener object.
        To learn how to use this class, see ReceiveTransmissions(port, eventhandler)

    Parameters:
        string peerID: the IP address of [the computer who wants to transmit data to s]
        int sender_port: the port on the sender computer to send our transmission status data to
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)
        function(bytearray data, string sender_peerID): the user-defined eventhandler to receive the data transmitted once the the transmission is finished
    """

    peerID = None
    port = 0
    eventhandler = None
    buffer_size = 0

    sender_port = None

    transmitter_finished = False
    transmission_finished = False
    buffers = list()
    lis_port = None
    trsm_lis_port = None
    buffer_size = None
    listener_thread = None

    trsm_replier = None

    def __init__(self, peerID, sender_port, buffer_size, eventhandler):
        self.peerID = peerID
        self.sender_port = sender_port
        self.buffer_size = buffer_size
        self.eventhandler = eventhandler

        # needed for some reason in conversations cause it otherwise keeps the values from the last transmission listener
        self.buffers = list()

        # setting up listener for receiving and processing the transmission self.buffers
        self.listener_thread = ListenToBuffersOnPort(
            self.ProcessTransmissionBuffer, 0, self.buffer_size, status_eventhandler=self.NoCommunication)
        self.trsm_lis_port = self.listener_thread.port
        CreateListeningConnection(str(self.trsm_lis_port), self.trsm_lis_port)
        if print_log_transmissions:
            print("Ready to receive transmission.")

        self.trsm_replier = CreateSendingConnection(peerID, str(sender_port))
        port = self.trsm_replier.getsockname()[1]
        #self.trsm_replier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.trsm_replier.connect(("127.0.0.1", port))
        # Telling sender we're ready to start receiving the transmission, telling him which self.port we're listening on
        self.SendBufferToPort(ToB255No0s(self.trsm_lis_port)
                              + bytearray([0]) + "start transmission".encode("utf-8"))

    # function for easily replying to sender using the self.port and self.buffer_size they specified

    def SendBufferToPort(self, buffer):
        try:
            self.trsm_replier.send(AddIntegrityByteToBuffer(buffer))
        except:
            if print_log:
                print("Communication to transmitter has broken down")
            if not self.transmission_finished:
                self.FinishedTransmission(False)

    # Processes the buffers received over the transmission
    def ProcessTransmissionBuffer(self, data, peerID):
        if self.transmission_finished:
            self.SendBufferToPort("finished transmission".encode("utf-8"))
            return
        # Performing buffer integrity check
        integrity_byte = data[0]
        data = data[1:]
        sum = 0
        for byte in data:
            sum += byte
            if sum > 65000:  # if the sum is reaching the upper limit of an unsigned 16-bit integer
                sum = sum % 256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
        # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
        if sum % 256 != integrity_byte:
            if print_log:
                print("Received a buffer with a non-matching integrity byte")
                print(data)
            return

        # decoding the transission buffer
        if(data == "finished transmission".encode("utf-8")):
            if print_log_transmissions:
                print("Sender finished transmission")
            self.transmitter_finished = True
            missing_buffer_count = 0
            index = 0
            for buffer in self.buffers:
                if(buffer == bytearray()):
                    self.SendBufferToPort(ToB255No0s(index)
                                          + bytearray([0]) + "resend".encode("utf-8"))
                    if print_log_transmissions:
                        print("Requested buffer", index, "to be resent")
                    missing_buffer_count += 1
                index += 1
            if(missing_buffer_count == 0):
                self.FinishedTransmission()

            return

        index = data.index(bytearray([0]))
        buffer_No = FromB255No0s(data[0:index])
        data = data[index + 1:]

        if print_log_transmissions:
            print("received transmission buffer" + str(buffer_No))

        content = data

        # Adding empty entries to the sorted buffer list if the list doesn't have an entry for this buffer yet
        while buffer_No >= len(self.buffers):
            self.buffers.append(bytearray())
        self.buffers[buffer_No] = content

        # sending confirmation buffer so that the sender knows we've received this buffer
        self.SendBufferToPort(ToB255No0s(buffer_No)
                              + bytearray([0]) + "conf".encode("utf-8"))

        if self.transmitter_finished:
            missing_buffer_count = 0
            index = 0
            for buffer in self.buffers:
                if(buffer == bytearray()):
                    missing_buffer_count += 1

            if(missing_buffer_count == 0):
                self.FinishedTransmission()
            return

    def NoCommunication(self, time_since_last):
        if self.transmission_finished:
            return
        if print_log_transmissions:
            print("NO COMMUNICATION " + str(time_since_last))
        if(time_since_last > close_timeout_sec):
            print("Aborting data transmission due to no response from receiver.")
            if not self.transmission_finished:
                self.FinishedTransmission(False)
        elif(time_since_last > resend_timeout_sec):
            if print_log_transmissions:
                print("Resending transmission confirmation.")
            self.SendBufferToPort(ToB255No0s(self.trsm_lis_port)
                                  + bytearray([0]) + "start transmission".encode("utf-8"))

    def FinishedTransmission(self, succeeded=True):
        if self.transmission_finished:
            return
        self.transmission_finished = True

        if succeeded:
            self.SendBufferToPort("finished transmission".encode("utf-8"))
            if print_log_transmissions:
                print("Transmission finished.")
            data = bytearray()

            for buffer in self.buffers:
                data = data + buffer

            _thread.start_new_thread(self.eventhandler, (data, self.peerID))

        else:
            if print_log:
                print("Transmission failed.")

        def CloseConnections():
            time.sleep(30)
            self.listener_thread.Terminate()
            self.trsm_replier.close()
            CloseListeningConnection(
                str(self.trsm_lis_port), self.trsm_lis_port)
            CloseSendingConnection(self.peerID, str(self.sender_port))
        Thread(target=CloseConnections).start()


def AddIntegrityByteToBuffer(buffer):
    # Adding an integrity byte that equals the sum of all the bytes in the buffer modulus 256
    # to be able to detect data corruption:
    sum = 0
    for byte in buffer:
        sum += byte
        if sum > 65000:  # if the sum is reaching the upper limit of an unsigned 16-bit integer
            sum = sum % 256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
    # adding the integrity byte to the start of the buffer
    return bytearray([sum % 256]) + buffer


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


def SplitBy255(bytes):
    result = list()
    pos = 0
    collected = list()
    while pos < len(bytes):
        if bytes[pos] == 255:
            result.append(bytearray(collected))
            collected = list()
        else:
            collected.append(bytes[pos])
        pos += 1
    result.append(bytearray(collected))
    return result
