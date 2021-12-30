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

from queue import Queue
import socket
import zmq
import threading
from threading import Thread, Event
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
zmq_context = zmq.Context()


# -------------- Settings ---------------------------------------------------------------------------------------------------
print_log = False  # whether or not to print debug in output terminal
print_log_connections = False
print_log_transmissions = True
print_log_conversations = True
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
transmission_request_timeout_sec = 3
transmission_request_max_retriies = 3
transmission_receive_timeout_sec = 5

def_buffer_size = 4096  # the communication buffer size
# the size of the chunks into which files should be split before transmission
def_block_size = 1048576

free_sending_ports = [x for x in range(20001, 20500)]

# -------------- User Functions ----------------------------------------------------------------------------------------------
# Transmits a bytearray of any length to the specified host.
# Returns a transmitter object so that the status of the transmission can be monitored


def TransmitData(data, peerID, req_lis_name, buffer_size=def_buffer_size, await_finish=False, on_finish_handler=None):
    def SendTransmissionRequest():
        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        # sock.connect(("127.0.0.1", port))
        data = AddIntegrityByteToBuffer(IPFS_API.MyID().encode(
        ) + bytearray([255]) + ToB255No0s(our_port) + bytearray([0]) + ToB255No0s(buffer_size))
        tries = 0
        poller = zmq.Poller()
        while(tries < transmission_request_max_retriies):
            sock = CreateSendingConnection(peerID, req_lis_name)
            success = sock.send(data)
            if print_log_transmissions:
                print(str(our_port)
                      + ": Sent transmission request to " + str(req_lis_name))

            poller.register(sock, zmq.POLLIN)
            evts = poller.poll(transmission_request_timeout_sec*1000)

            poller.unregister(sock)
            sock.close()
            del sock
            CloseSendingConnection(peerID, req_lis_name)
            if len(evts) > 0:
                if print_log_transmissions:
                    print(str(our_port)
                          + ": Transmission request to " + str(req_lis_name) + "was received.")
                return True  # signal success
            else:
                if print_log_transmissions:
                    print(str(our_port)
                          + ": Transmission request send " + str(req_lis_name) + "timeout reached.")
            tries += 1
        return False    # signal Failure
    while True:
        sock = zmq_context.socket(zmq.REP)
        our_port = sock.bind_to_random_port("tcp://*")
        CreateListeningConnection(str(our_port), our_port)

        poller = zmq.Poller()
        poller.register(sock, zmq.POLLIN)
        if SendTransmissionRequest():
            evts = poller.poll(transmission_request_timeout_sec*1000)
            if len(evts) > 0 and sock.recv() == b"start transmission":
                poller = zmq.Poller()
                poller.register(sock, zmq.POLLIN)
                sock.send(data)
                evts = poller.poll(transmission_request_timeout_sec*1000)

                if len(evts) > 0 and sock.recv() == b'Finished!':
                    sock.close()

                    CloseListeningConnection(str(our_port), our_port)
                    CloseSendingConnection(peerID, req_lis_name)

                    if print_log_transmissions:
                        print(str(our_port) + ": Finished transmission.")

                    if on_finish_handler:
                        on_finish_handler(True)

                    return True  # signal success
                else:
                    sock.close()
                    return False
            else:
                print("RECIEVED OTHER DATA")
        else:
            sock.close()
            return False


# Sets itself up to receive data transmissions, transmitted by the sender using the TransmitData function.
# Returns the Listener object so that receiving the data transmissions can be stopped by calling listener.Terminate().


class ListenForTransmissions:
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
    terminate = False

    def ReceiveTransmissionRequests(self, data):
        if print_log_transmissions:
            print(self.listener_name + ": processing transmission request...")
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
                        self.listener_name + ": Received a buffer with a non-matching integrity buffer")
                return

            index = data.index(bytearray([255]))
            peerID = data[0:index].decode()
            data = data[index + 1:]

            index = data.index(bytearray([0]))
            sender_port = FromB255No0s(data[0:index])
            data = data[index + 1:]

            buffer_size = FromB255No0s(data)
            if print_log_transmissions:
                print(
                    self.listener_name + ": Received transmission request.")
            listener = Thread(target=self.ReceiveTransmission, args=(
                peerID, sender_port, buffer_size, self.eventhandler))
            listener.start()
            return listener

        except Exception as e:
            print("")
            print(
                self.listener_name + ": Exception in NetTerm.ReceiveTransmissions.ReceiveTransmissionRequests()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print(self.listener_name + ": Could not decode transmission request.")

    def ReceiveTransmission(self, peerID, sender_port, buffer_size, eventhandler):
        sock = CreateSendingConnection(peerID, str(sender_port))

        if print_log_transmissions:
            print("Ready to receive transmission.")

        poller = zmq.Poller()
        poller.register(sock, zmq.POLLIN)

        sock.send(b"start transmission")
        evts = poller.poll(transmission_receive_timeout_sec*1000)
        if len(evts) == 0:
            CloseSendingConnection(peerID, str(sender_port))
            if print_log:
                print("Transmission reception failed.")
        data = sock.recv()
        sock.send("Finished!".encode())
        sock.close()
        _thread.start_new_thread(eventhandler, (data, peerID))
        CloseSendingConnection(peerID, str(sender_port))

    def Listen(self):
        # context = zmq.Context()
        self.socket = zmq_context.socket(zmq.REP)
        self.port = self.socket.bind_to_random_port("tcp://*")
        CreateListeningConnection(self.listener_name, self.port)
        if print_log_transmissions:
            print(self.listener_name
                  + ": Listening for transmission requests as " + self.listener_name)
        while self.socket:
            data = self.socket.recv()
            if self.terminate:
                self.socket.send(b"Righto.")
                return
            if self.ReceiveTransmissionRequests(data):
                self.socket.send(b"Transmission request accepted.")
            else:
                self.socket.send(b"Transmission request not accepted.")

    def __init__(self, listener_name, eventhandler):
        self.listener_name = listener_name
        self.eventhandler = eventhandler
        self.listener = Thread(target=self.Listen, args=())
        self.listener.start()

    def Terminate(self):
        # self.socket.unbind(self.port)
        self.terminate = True
        CloseListeningConnection(self.listener_name, self.port)
        socket = zmq_context.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:{self.port}")
        socket.send("close".encode())
        socket.recv()
        socket.close()
        del socket
        self.socket.close()
        del self.socket
        del self.listener


def StartConversation(conversation_name, peerID, others_req_listener, eventhandler=None):
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
        # forwards communication from any conversation to the OnReceive function
        ListenForConversations("conv listener", OnReceive)

    Parameters:
        1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
        2. peerID: the IPFS peer ID of the node to communicate with
        3. others_req_listener: the name of the ther peer's conversation listener object
    """
    conv = Conversation()
    conv.Start(conversation_name, peerID, others_req_listener, eventhandler)
    return conv


def StartConversationAwait(conversation_name, peerID, others_req_listener, eventhandler=None):
    """Starts a conversation object with which peers can send data transmissions to each other.
    Waits (Blocks the calling thread) until the target peer has joined the conversation.
    Sends a conversation request to the other peer's conversation request listener which the other peer must accept (joining the conversation) in order to start the conversation.

    Usage:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = StartConversation("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        # the other peer must have a conversation listener named "conv listener" running, e.g. via:
        # forwards communication from any conversation to the OnReceive function
        ListenForConversations("conv listener", OnReceive)

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
        # forwards communication from any conversation to the OnReceive function
        ListenForConversations("conv listener", OnReceive)

    Methods:
        Start: start a conversation with another peer, continuing code execution without waiting for the other peer to join.
        StartAwait: start a conversation with another peer, waiting (blocking the calling thread) until the other peer to join.
            # Note: Start and StartAwait send a conversation request to the other peer's conversation request listener which the other peer must accept (joining the conversation) in order to start the conversation.
        Join: join a conversation which another peer started. Used by a conversation listener. See ListenForConversations for usage.
    """
    conversation_started = False
    # started = Event()
    # last_message = None
    # message_received = Event()
    eventhandler = None
    message_queue = Queue()

    def __init__(self):
        self.started = Event()

    def Start(self, conversation_name, peerID, others_req_listener, eventhandler=None):
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
            # forwards communication from any conversation to the OnReceive function
            ListenForConversations("conv listener", OnReceive)

        Parameters:
            1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID: the IPFS peer ID of the node to communicate with
            3. others_req_listener: the name of the ther peer's conversation listener object
        """
        if(print_log_conversations):
            print(conversation_name + ": Starting conversation")
        self.conversation_name = conversation_name
        self.eventhandler = eventhandler

        # def AwaitResponse(data, peerID):
        #     info = SplitBy255(data)
        #     if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
        #         self.others_conv_listener = info[1].decode('utf-8')
        #         # self.hear_eventhandler = self.Hear
        #         self.conversation_started = True
        #         if print_log_conversations:
        #             print(conversation_name + ": peer joined, conversation started")
        #         self.started.set()
        #     elif print_log_conversations:
        #         print(conversation_name + ": received unrecognisable buffer, expected join confirmation")
        #         print(info[0])
        # self.hear_eventhandler = AwaitResponse
        self.peerID = peerID
        if print_log_conversations:
            print(conversation_name + ": sending conversation request")
        self.listener = ListenForTransmissions(conversation_name, self.Hear)
        # self.listener = ListenForTransmissions(conversation_name, self.hear_eventhandler)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        TransmitData(data, peerID, others_req_listener)
        if print_log_conversations:
            print(conversation_name + ": sent conversation request")

    def StartAwait(self, conversation_name, peerID, others_req_listener, eventhandler=None):
        """Starts a conversation object with which peers can send data transmissions to each other.
        Waits (Blocks the calling thread) until the target peer has joined the conversation.
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            # forwards communication from any conversation to the OnReceive function
            ListenForConversations("conv listener", OnReceive)

        Parameters:
            1. conversation_name: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID: the IPFS peer ID of the node to communicate with
            3. others_req_listener: the name of the ther peer's conversation listener object
        """
        self.Start(conversation_name, peerID,
                   others_req_listener, eventhandler)
        self.started.wait()

    def Join(self, conversation_name, peerID, others_conv_listener, eventhandler=None):
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
        self.conversation_started = True
        TransmitData(data, peerID, others_conv_listener)
        if print_log_conversations:
            print(conversation_name + ": Joined conversation "
                  + others_conv_listener)

    def Hear(self, data, peerID, arg3=""):
        """
        Receives data from the conversation and forwards it to the user's eventhandler
        """
        # print("HEAR", data)
        if not data:
            print("CONV.HEAR: RECEIVED NONE")
            return

        if not self.conversation_started:
            info = SplitBy255(data)
            if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
                self.others_conv_listener = info[1].decode('utf-8')
                # self.hear_eventhandler = self.Hear
                self.conversation_started = True
                if print_log_conversations:
                    print(self.conversation_name + ": peer joined, conversation started")
                self.started.set()

            elif print_log_conversations:
                print(self.conversation_name +
                      ": received unrecognisable buffer, expected join confirmation")
                print(info[0])
            return
        # if self.conversation_started:
        # self.last_message = data
        # self.message_received.set()

        self.message_queue.put(data)
        # self.message_received.clear()
        # self.message_received = Event()

        if self.eventhandler:
            if len(signature(self.eventhandler).parameters) == 2:    # if the eventhandler has 2 parameters
                Thread(target=self.eventhandler, args=(self, data)).start()
            else:
                Thread(target=self.eventhandler, args=(self, data, arg3)).start()

    def Listen(self):
        """Waits until the conversation peer sends a message, then returns that message."""
        data = self.message_queue.get()
        if data:
            return data
        else:
            if print_log_conversations:
                print("Conv.Listen: received", self.last_message, "restarting Event Wait")
            self.Listen()
            return
        self.message_received.clear()

        # self.message_received.wait()
        # if self.last_message:
        #     return self.last_message
        # else:
        #     if print_log_conversations:
        #         print("Conv.Listen: received", self.last_message, "restarting Event Wait")
        #     self.Listen()

    def Say(self, data, buffer_size=def_buffer_size, await_finish=False):
        """Transmits data of any length to the other peer.
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            # forwards communication from any conversation to the OnReceive function
            ListenForConversations("conv listener", OnReceive)
        """
        while not self.conversation_started:
            if print_log:
                print("Wanted to say something but conversation was not yet started")
            time.sleep(0.01)
        TransmitData(data, self.peerID, self.others_conv_listener,
                     buffer_size, await_finish)
        return True

    def SayAwait(self, data, buffer_size=def_buffer_size, await_finish=False):
        """Transmits data of any length to the other peer.
        Usage:
            def OnReceive(conversation, data):
                print(data.decode("utf-8"))

            conversation = Conversation()
            conversation.StartAwait("test", "QmHash", "conv listener", OnReceive)
            conversation.Say("Hello there!".encode())

            # the other peer must have a conversation listener named "conv listener" running, e.g. via:
            # forwards communication from any conversation to the OnReceive function
            ListenForConversations("conv listener", OnReceive)
        """
        if not self.conversation_started:
            if print_log:
                print("Wanted to say something but conversation was not yet started")
            self.started.wait()
        TransmitData(data, self.peerID, self.others_conv_listener,
                     buffer_size)
        return True

    def Close(self):
        self.listener.Terminate()
        self = None

    def __del__(self):
        self.Close()


class ConversationListener:
    def __init__(self, listener_name, eventhandler):
        self.listener_name = listener_name
        if(print_log_conversations):
            print("Listening for conversations as " + listener_name)
        self.eventhandler = eventhandler
        self.listener = ListenForTransmissions(
            listener_name, self.OnRequestReceived)

    def OnRequestReceived(self, data, peerID):
        if print_log_conversations:
            print(f"ConvLisReceived {self.listener_name}: Received Conversation Request")
        info = SplitBy255(data)
        if info[0] == bytearray("I want to start a conversation".encode('utf-8')):
            if print_log_conversations:
                print(f"ConvLisReceived {self.listener_name}: Starting conversation...")
            conversation_name = info[1].decode('utf-8')
            self.eventhandler(conversation_name, peerID)
        elif print_log_conversations:
            print(f"ConvLisReceived {self.listener_name}: Received unreadable request")
            print(info[0])


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
    status = "not started"  # "transitting" "finished" "aborted"

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
        self.status = "transmitting"
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
        self.status = "finished"

    def Hear(self, conv, data):
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": received response from receiver")
        info = SplitBy255(data)
        if info[0].decode('utf-8') == "ready":
            self.StartTransmission()


class FileTransmissionReceiver:
    transmission_started = False
    status = "not started"  # "receiving" "finished" "aborted"

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
        self.status = "receiving"

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
        self.status = "finished"
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

    sock = zmq_context.socket(zmq.REQ)
    # socket.CONNECT_TIMEOUT = 1
    if port == None:
        for prt in free_sending_ports:
            try:
                ForwardFromPortToPeer(protocol, prt, peerID)
                sock.connect(f"tcp://localhost:{prt}")
                return sock
            except:
                pass

        print("failed to find free port for sending connection")
    else:
        ForwardFromPortToPeer(protocol, port, peerID)
        sock.connect(f"tcp://localhost:{prt}")
        return sock


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
            if print_log_connections:
                print(f"listening fas \"{protocol}\" on {port}")
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
    # thread = _thread.start_new_thread(ListenIndefinately,())

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

        # _thread.start_new_thread(eventhandler, (data, peerID))
        self.sock.close()
        if print_log_connections:
            print("Closed listener.")

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    # thread = _thread.start_new_thread(ListenIndefinately,())

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
    # thread = _thread.start_new_thread(ListenIndefinately,())

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

        # _thread.start_new_thread(eventhandler, (data, peerID))
        self.sock.close()
        if print_log_connections:
            print("Closed listener.")

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    # thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def Terminate(self):
        self.terminate = True   # marking the terminate flag as true
        # self.sock.close()
        # SendBufferToPort(bytearray([0]),"127.0.0.1",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop


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
