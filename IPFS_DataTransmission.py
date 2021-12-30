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
print_log_transmissions = False
print_log_conversations = True
print_log_files = True

if not print_log:
    print_log_connections = False
    print_log_transmissions = False
    print_log_conversations = False
    print_log_files = False


resend_timeout_sec = 1
close_timeout_sec = 100
transmission_send_timeout_sec = 3
transmission_request_max_retries = 3
transmission_send_timeout_sec = 5
transmission_receive_timeout_sec = 5

def_buffer_size = 4096  # the communication buffer size
# the size of the chunks into which files should be split before transmission
def_block_size = 1048576

sending_ports = [x for x in range(20001, 20500)]

# -------------- User Functions ----------------------------------------------------------------------------------------------


def TransmitData(data: bytes, peerID: str, req_lis_name: str, timeout_sec: int = transmission_send_timeout_sec, max_retries: int = transmission_request_max_retries):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified IPFS peer ID.

    Usage:
        success = TransmitData("data to transmit".encode("utf-8"), "Qm123456789", "applicationNo2")    # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        timeout_sec: connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        max_retries: how often the transmission should be reattempted when the timeout is reached
    Returns:
        bool success: whether or not the transmission succeeded
    """
    def SendTransmissionRequest():
        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        # sock.connect(("127.0.0.1", port))
        data = AddIntegrityByteToBuffer(IPFS_API.MyID().encode(
        ) + bytearray([255]) + ToB255No0s(our_port))
        tries = 0
        poller = zmq.Poller()
        while max_retries == -1 or tries < max_retries:
            sock = CreateSendingConnection(peerID, req_lis_name)
            success = sock.send(data)
            if print_log_transmissions:
                print(str(our_port)
                      + ": Sent transmission request to " + str(req_lis_name))

            poller.register(sock, zmq.POLLIN)
            evts = poller.poll(timeout_sec*1000)

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
                          + ": Transmission request send " + str(req_lis_name) + "timeout_sec reached.")
            tries += 1
        CloseSendingConnection(peerID, req_lis_name)
        return False    # signal Failure

    sock = zmq_context.socket(zmq.REP)
    our_port = sock.bind_to_random_port("tcp://*")
    CreateListeningConnection(str(our_port), our_port)

    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    if SendTransmissionRequest():
        evts = poller.poll(timeout_sec*1000)    # wait for receiver to signal readiness
        if len(evts) > 0 and sock.recv() == b"start transmission":
            poller = zmq.Poller()
            poller.register(sock, zmq.POLLIN)
            sock.send(data)  # transmit Data
            evts = poller.poll(timeout_sec*1000)

            if len(evts) > 0 and sock.recv() == b'Finished!':
                sock.close()

                CloseListeningConnection(str(our_port), our_port)

                if print_log_transmissions:
                    print(str(our_port) + ": Finished transmission.")

                return True  # signal success

    sock.close()
    CloseListeningConnection(str(our_port), our_port)
    return False    # signal Failure


def ListenForTransmissions(listener_name, eventhandler):
    """
    Listens for incoming transmission requests (senders requesting to transmit data to us)
    and sets up the machinery needed to receive those transmissions.

    Usage:
        def OnReceive(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        # listening with a Listener-Name of "applicationNo2"
        listener = ListenForTransmissions("applicationNo2", OnReceive)

        # When we no longer want to receive any transmissions:
        listener.Terminate()

    Parameters:
        string listener_name: the name of this TransmissionListener (chosen by user, allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        function(bytearray data, string peerID) eventhandler: the function that should be called when a transmission of data is received
    """
    return TransmissionListener(listener_name, eventhandler)


class TransmissionListener:
    """
    Listens for incoming transmission requests (senders requesting to transmit data to us) and sets up the machinery needed to receive those transmissions.

    Usage:
        def OnReceive(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        # listening with a Listener-Name of "applicationNo2"
        listener = TransmissionListener("applicationNo2", OnReceive)

        # When we no longer want to receive any transmissions:
        listener.Terminate()

    Parameters:
        string listener_name: the name of this TransmissionListener (chosen by user, allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        function(bytearray data, string peerID) eventhandler: the function that should be called when a transmission of data is received
    """
    # This function itself is called to process the transmission request buffer sent by the transmission sender.
    terminate = False

    def __init__(self, listener_name, eventhandler):
        self.listener_name = listener_name
        self.eventhandler = eventhandler
        self.listener = Thread(target=self.Listen, args=())
        self.listener.start()

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
            sender_port = FromB255No0s(data)

            if print_log_transmissions:
                print(
                    self.listener_name + ": Received transmission request.")
            listener = Thread(target=self.ReceiveTransmission, args=(
                peerID, sender_port, self.eventhandler))
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

    def ReceiveTransmission(self, peerID, sender_port, eventhandler):
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
            return
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
    """
    Starts a conversation object with which 2 peers can repetatively make
    data transmissions to each other asynchronously and bidirectionally.

    Sends a conversation request to the other peer's conversation request listener
    which the other peer must accept (joining the conversation) in order to start the conversation.
    Usage:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = StartConversation("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        ## The other peer must have a conversation listener named "conv listener" running, e.g. via:
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
    print("IPFS_API: WARNING: This function is deprecated.Please use StartConversation() instead.\n" +
          "The reason for this is the introduction of a proper failure handling system.\n")
    return StartConversation(conversation_name, peerID,
                             others_req_listener, eventhandler)


def ListenForConversations(conv_name, eventhandler):
    """
    Listen to incoming conversation requests.
    Whenever a new conversation request is received, the specified eventhandler
    is called which must then decide whether or not to join the conversation, 
    and then act upon that decision.

    Usage Example:

        def NewConvHandler(conversation_name, peerID):
            print("Joining a new conversation:", conversation_name)

            # create Conversation object
            conv = IPFS_DataTransmission.Conversation()
            # join the conversation with the other peer
            conv.Join(conversation_name, peerID, conversation_name, OnMessageReceived)
            print("joined")

            # Start communicating with other peer
            data = conv.Listen()
            print("Received data: ", data)
            conv.Say("Hi back".encode("utf-8"))


    conv_lis = IPFS_DataTransmission.ListenForConversations(
        "general_listener", NewConvHandler)
    """
    return ConversationListener(conv_name, eventhandler)


class Conversation:
    """
    Communication object which allows 2 peers to repetatively make
    data transmissions to each other asynchronously and bidirectionally.
    Usage example:
        ## Conversation Initiator:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = Conversation()
        conversation.Start("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        ## The other peer must have a conversation listener named "conv listener" running, e.g. via:
        # forwards communication from any conversation to the OnReceive function
        ListenForConversations("conv listener", OnReceive)

    Methods:
        Start: start a conversation with another peer, waiting for the other peer to join.
            # Note: Start sends a conversation request to the other peer's
            conversation request listener which the other peer must accept
            (joining the conversation) in order to start the conversation.
        Join: join a conversation which another peer started. Used by a
                conversation listener. See ListenForConversations for usage.
        Say: send some data to the other peer.
        Listen: wait until the other peer sends us some data
                (can be used as an alternative to the event handler which is
                optionally specified in the Start() or Join() methods)
    """
    conversation_started = False
    # started = Event()
    # last_message = None
    # message_received = Event()
    eventhandler = None
    message_queue = Queue()

    def __init__(self):
        self.started = Event()

    def Start(self, conversation_name, peerID, others_req_listener, eventhandler=None, timeout_sec=transmission_send_timeout_sec, max_retries=transmission_request_max_retries):
        """Starts a conversation object with which peers can send data transmissions to each other.
        Code blocks until the other peer joins the conversation or timeout is reached
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
        Returns:
            bool success: whether or not the conversation with the peer was successfully started
        """
        if(print_log_conversations):
            print(conversation_name + ": Starting conversation")
        self.conversation_name = conversation_name
        self.eventhandler = eventhandler

        self.peerID = peerID
        if print_log_conversations:
            print(conversation_name + ": sending conversation request")
        self.listener = ListenForTransmissions(conversation_name, self.Hear)
        # self.listener = ListenForTransmissions(conversation_name, self.hear_eventhandler)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        if TransmitData(data, peerID, others_req_listener, timeout_sec, max_retries):
            if print_log_conversations:
                print(conversation_name + ": sent conversation request")
            self.started.wait()
            return True     # signal success
        else:
            return False    # signal Failure

    def StartAwait(self, conversation_name, peerID, others_req_listener, eventhandler=None):
        print("IPFS_API: WARNING: This function is deprecated.Please use StartConversation() instead.\n" +
              "The reason for this is the introduction of a proper failure handling system.\n")
        return self.Start(self, conversation_name, peerID, others_req_listener, eventhandler=None)

    def Join(self, conversation_name, peerID, others_trsm_listener, eventhandler=None):
        """
        Joins a conversation which another peer started, given their peer ID
        and conversation's transmission-listener's name.
        Used by a conversation listener. See ListenForConversations for usage.
        Returns:
            bool success: whether or not the conversation with the peer was successfully joined
        """
        self.conversation_name = conversation_name
        if print_log_conversations:
            print(conversation_name + ": Joining conversation "
                  + others_trsm_listener)
        self.eventhandler = eventhandler
        self.listener = ListenForTransmissions(conversation_name, self.Hear)
        self.others_trsm_listener = others_trsm_listener
        self.peerID = peerID
        data = bytearray("I'm listening".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        self.conversation_started = True
        if TransmitData(data, peerID, others_trsm_listener):
            if print_log_conversations:
                print(conversation_name + ": Joined conversation "
                      + others_trsm_listener)
            return True  # signal success
        else:
            if print_log_conversations:
                print(conversation_name + ": Joined conversation "
                      + others_trsm_listener)
            return False    # signal failure

    def Hear(self, data, peerID, arg3=""):
        """
        Receives data from the conversation.
        Forwards it to the user's eventhandler if the conversation has already started,
        otherwise processes the converation initiation codes.
        """
        # print("HEAR", data)
        if not data:
            print("CONV.HEAR: RECEIVED NONE")
            return

        if not self.conversation_started:
            info = SplitBy255(data)
            if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
                self.others_trsm_listener = info[1].decode('utf-8')
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
        else:   # conversation has already started
            self.message_queue.put(data)

            if self.eventhandler:
                if len(signature(self.eventhandler).parameters) == 2:    # if the eventhandler has 2 parameters
                    Thread(target=self.eventhandler, args=(self, data)).start()
                else:
                    Thread(target=self.eventhandler, args=(self, data, arg3)).start()

    def Listen(self, timeout=None):
        """Waits until the conversation peer sends a message,
            then returns that message.
        Can be used as an alternative to specifying an eventhandler
            to process received messages, or in parallel.
        """
        if not timeout:
            data = self.message_queue.get()
        else:
            try:
                data = self.message_queue.get(timeout=timeout)
            except:  # timeout reached
                return None
        if data:
            return data
        else:
            if print_log_conversations:
                print("Conv.Listen: received", self.last_message, "restarting Event Wait")
            self.Listen()
            return

    def Say(self, data, timeout_sec=transmission_send_timeout_sec, max_retries=transmission_request_max_retries):
        """
        Transmits the input data (a bytearray of any length) to the other computer in this conversation.

        Usage:
            success = conv.Say("data to transmit".encode("utf-8"), "Qm123456789", "applicationNo2")    # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes

        Parameters:
            bytearray data: the data to be transmitted to the receiver
            string peerID: the IPFS peer ID of [the recipient computer to send the data to]
            string listener_name: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
            timeout_sec: connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
            max_retries: how often the transmission should be reattempted when the timeout is reached
        Returns:
            bool success: whether or not the transmission succeeded
        """
        while not self.conversation_started:
            if print_log:
                print("Wanted to say something but conversation was not yet started")
            time.sleep(0.01)
        return TransmitData(data, self.peerID, self.others_trsm_listener, timeout_sec, max_retries)

    def Close(self):
        self.listener.Terminate()

    def __del__(self):
        self.Close()


class ConversationListener:
    """
    Object which listens to incoming conversation requests.
    Whenever a new conversation request is received, the specified eventhandler
    is called which must then decide whether or not to join the conversation, 
    and then act upon that decision.

    Usage Example:

        def NewConvHandler(conversation_name, peerID):
            print("Joining a new conversation:", conversation_name)

            # create Conversation object
            conv = IPFS_DataTransmission.Conversation()
            # join the conversation with the other peer
            conv.Join(conversation_name, peerID, conversation_name, OnMessageReceived)
            print("joined")

            # Start communicating with other peer
            data = conv.Listen()
            print("Received data: ", data)
            conv.Say("Hi back".encode("utf-8"))


    conv_lis = IPFS_DataTransmission.ListenForConversations(
        "general_listener", NewConvHandler)
    """

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

    def Terminate(self):
        self.listener.Terminate()


def TransmitFile(filepath, peerID, others_req_listener, metadata=bytearray(), block_size=def_block_size):
    """Transmits the given file to the specified peer
    Usage:
        transmitter = TransmitFile("text.txt", "QMHash", "my_apps_filelistener", "testmeadata".encode())
    Paramaters:
        string filepath: the path of the file to transmit
        string peerID: the IPFS ID of the computer to send the file to
        string others_req_listener: the name of the ther peer's conversation listener object
        bytes metadata: optional metadata to send to the receiver
        int block_size: the FileTransmitter sends the file in chunks.
            This is the siize of those chunks in bytes (default 1MiB) 
    Returns:
        FileTransmitter file_transmitter: returned only if the transmission starts successfully
    """
    file_transmitter = FileTransmitter(filepath, peerID, others_req_listener, metadata, block_size)
    success = file_transmitter.Start()
    if success:
        return file_transmitter


def ListenForFileTransmissions(listener_name, eventhandler, dir="."):
    """
    Listens to incoming file transmission requests.
    Whenever a file is received, the specified eventhandler is called.

    Usage:
        def OnDataReceived(peer, file, metadata):
            print("Received file.")
            print("File metadata:", metadata.decode())
            print("Filepath:", file)
            print("Sender:", peer)


        fr = IPFS_DataTransmission.ListenForFileTransmissions(
            "my_apps_filelistener", OnDataReceived)
    """
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


class FileTransmitter:
    """Transmits the given file to the specified peer
    Usage:
        transmitter = TransmitFile("text.txt", "QMHash", "filelistener", "testmeadata".encode())
    Paramaters:
        string filepath: the path of the file to transmit
        string peerID: the IPFS ID of the computer to send the file to
        string others_req_listener: the name of the ther peer's conversation listener object
        bytes metadata: optional metadata to send to the receiver
        int block_size: the FileTransmitter sends the file in chunks.
            This is the siize of those chunks in bytes (default 1MiB) 
    Returns:
        FileTransmitter file_transmitter: returned only if the transmission starts successfully
    """
    status = "not started"  # "transitting" "finished" "aborted"

    def __init__(self, filepath, peerID, others_req_listener, metadata=bytearray(), block_size=def_block_size):
        self.filesize = os.path.getsize(filepath)
        self.filename = os.path.basename(filepath)
        self.filepath = filepath
        self.metadata = metadata
        self.block_size = block_size
        self.peerID = peerID
        self.others_req_listener = others_req_listener

        print("IPFS_API: WARNING: In this new version the FileTransmitter no longer starts automatically.\n" +
              "Call the Start() function to start the transmission." +
              "The reason for this is the introduction of a proper failure handling system.\n")

    def Start(self):
        """
        Returns:
            bool success: whether or not file transmission was successfully started
        """
        self.conv_name = self.filename + "_conv"
        self.conversation = Conversation()
        if self.conversation.Start(
                self.conv_name, self.peerID, self.others_req_listener, self.Hear):
            self.conversation.Say(
                ToB255No0s(self.filesize) + bytearray([255])
                + bytearray(self.filename.encode()) + bytearray([255]) + self.metadata)
            if print_log_files:
                print("FileTransmission: " + self.filename
                      + ": Sent transmission request")
            return True
        else:
            return False

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
                self.conversation.Say(data)
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": finished file transmission")
        self.status = "finished"
        self.conversation.Close()

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
                if print_log_files:
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
        self.conv.Close()
        if signature(self.eventhandler).parameters.get("metadata") != None:
            self.eventhandler(self.conv.peerID, os.path.join(
                self.dir, self.filename), self.metadata)
        else:
            self.eventhandler(self.conv.peerID, os.path.join(
                self.dir, self.filename))


# ----------IPFS Technicalitites-------------------------------------------
connections_send = list()
connections_listen = list()


def CreateSendingConnection(peerID: str, protocol: str, port=None):
    IPFS_API.ClosePortForwarding(
        targetaddress="/p2p/" + peerID, protocol="/x/" + protocol)

    sock = zmq_context.socket(zmq.REQ)
    # socket.CONNECT_TIMEOUT = 1
    if port == None:
        for prt in sending_ports:
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
        protocol=f"/x/{protocol}", targetaddress=f"/ip4/127.0.0.1/tcp/{port}")


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
