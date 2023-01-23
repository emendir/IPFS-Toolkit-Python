"""
This is a module that enables the user to transmit and receive transmissions of data over the Interplanetary File System's P2P network (libp2p).
To use it you must have IPFS running on your computer.
Configure IPFS to enable all this:
ipfs config --json Experimental.Libp2pStreamMounting true
"""
from pdb import set_trace as debug
import shutil
from queue import Queue, Empty as QueueEmpty
import socket
import threading
from threading import Thread, Event
from datetime import datetime
import time
import traceback
import os
import inspect
from inspect import signature
from Errors import (DataTransmissionError, PeerNotFound, InvalidPeer,
                    CommunicationTimeout, UnreadableReply, ListenTimeout,
                    IPFS_Error)
try:
    import IPFS_API
except:
    import IPFS_API_Remote_Client as IPFS_API


# -------------- Settings ---------------------------------------------------------------------------------------------------
print_log = False  # whether or not to print debug in output terminal
print_log_connections = False
print_log_transmissions = False
print_log_conversations = False
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


def TransmitData(
        data: bytes,
        peerID: str,
        req_lis_name: str,
        timeout_sec: int = transmission_send_timeout_sec,
        max_retries: int = transmission_request_max_retries):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified IPFS peer ID.

    Usage:
        # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes
        success = TransmitData("data to transmit".encode(
            "utf-8"), "Qm123456789", "applicationNo2")

    Parameters:
        data:bytearray: the data to be transmitted to the receiver
        string peerID:str: the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name:str: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        transmission_send_timeout_sec:int: connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        transmission_request_max_retries:int: how often the transmission should be reattempted when the timeout is reached
    Returns:
        bool success: whether or not the transmission succeeded
    """
    if peerID == IPFS_API.MyID():
        raise InvalidPeer(
            message="You cannot use your own IPFS peer ID as the recipient.")

    def SendTransmissionRequest():
        """
        Send s transmission request to the recipient.
        """
        request_data = AddIntegrityByteToBuffer(IPFS_API.MyID().encode())
        tries = 0

        # repeatedly try to send transmission request to recipient until a reply is received
        while max_retries == -1 or tries < max_retries:
            if print_log_transmissions:
                print("Sending transmission request to " + str(req_lis_name))
            sock = CreateSendingConnection(peerID, req_lis_name)
            sock.sendall(request_data)
            if print_log_transmissions:
                print("Sent transmission request to " + str(req_lis_name))

            # reply = sock.recv(def_buffer_size)
            reply = recv_timeout(sock, timeout_sec)
            # recv_timeout
            sock.close()
            del sock
            CloseSendingConnection(peerID, req_lis_name)
            if reply:
                try:
                    their_trsm_port = reply[30:].decode()  # signal success
                    if their_trsm_port:
                        if print_log_transmissions:
                            print("Transmission request to " +
                                  str(req_lis_name) + "was received.")
                        return their_trsm_port
                    else:
                        raise UnreadableReply()
                except:
                    raise UnreadableReply()
            else:
                if print_log_transmissions:
                    print("Transmission request send " +
                          str(req_lis_name) + "timeout_sec reached.")
            tries += 1
        CloseSendingConnection(peerID, req_lis_name)
        raise CommunicationTimeout(
            "Received no response from peer while sending transmission request.")

    their_trsm_port = SendTransmissionRequest()
    sock = CreateSendingConnection(peerID, their_trsm_port)
    sock.sendall(data)  # transmit Data
    if print_log_transmissions:
        print("Sent Transmission Data", data)
    response = sock.recv(def_buffer_size)
    if response and response == b"Finished!":
        # conn.close()
        sock.close()
        CloseSendingConnection(peerID, their_trsm_port)
        if print_log_transmissions:
            print(": Finished transmission.")
        return True  # signal success
    else:
        if print_log_transmissions:
            print("Received unrecognised response:", response)
        raise UnreadableReply()
    # sock.close()
    # CloseSendingConnection(peerID, their_trsm_port)


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
        self.listener = Thread(target=self.Listen, args=(),
                               name=f"DataTransmissionListener-{listener_name}")
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

            peerID = data.decode()

            if print_log_transmissions:
                print(
                    self.listener_name + ": Received transmission request.")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            our_port = sock.getsockname()[1]
            CreateListeningConnection(str(our_port), our_port)
            sock.listen()

            listener = Thread(target=self.ReceiveTransmission, args=(
                peerID, sock, our_port, self.eventhandler), name=f"DataTransmissionReceiver-{our_port}")
            listener.start()
            return our_port

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

    def ReceiveTransmission(self, peerID, sock, our_port, eventhandler):
        #
        # sock = CreateSendingConnection(peerID, str(sender_port))
        #
        # if print_log_transmissions:
        #     print("Ready to receive transmission.")
        #
        # sock.sendall(b"start transmission")
        if print_log_transmissions:
            print("waiting to receive actual transmission")
        conn, addr = sock.accept()
        if print_log_transmissions:
            print("received connection response fro actual transmission")
        data = recv_timeout(conn)
        conn.send("Finished!".encode())
        # conn.close()
        Thread(target=eventhandler, args=(data, peerID),
               name="TransmissionListener.ReceivedTransmission").start()
        CloseListeningConnection(str(our_port), our_port)
        sock.close()

    def Listen(self):
        if print_log_transmissions:
            print("Creating Listener")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        CreateListeningConnection(self.listener_name, self.port)

        if print_log_transmissions:
            print(self.listener_name
                  + ": Listening for transmission requests as " + self.listener_name)
        self.socket.listen()
        while True:
            conn, addr = self.socket.accept()
            data = recv_timeout(conn)
            if self.terminate:
                # conn.sendall(b"Righto.")
                conn.close()
                self.socket.close()
                return
            port = self.ReceiveTransmissionRequests(data)
            if port:
                conn.send(f"Transmission request accepted.{port}".encode())
            else:
                conn.send(b"Transmission request not accepted.")

    def Terminate(self):
        # self.socket.unbind(self.port)
        self.terminate = True
        CloseListeningConnection(self.listener_name, self.port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", self.port))
            sock.sendall("close".encode())
            # recv_timeout(sock)
            sock.close()
            del sock
        except:
            pass

    def __del__(self):
        self.Terminate()


def StartConversation(conversation_name,
                      peerID,
                      others_req_listener,
                      data_received_eventhandler=None,
                      file_eventhandler=None,
                      file_progress_callback=None,
                      encryption_callbacks=None,
                      timeout_sec=transmission_send_timeout_sec,
                      max_retries=transmission_request_max_retries,
                      dir="."):
    """
    Starts a conversation object with which 2 peers can repetatively make
    data transmissions to each other asynchronously and bidirectionally.

    Sends a conversation request to the other peer's conversation request listener
    which the other peer must accept (joining the conversation) in order to start the conversation.
    Usage:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = StartConversation(
            "test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        # The other peer must have a conversation listener named "conv listener" running, e.g. via:
        # forwards communication from any conversation to the OnReceive function
        ListenForConversations("conv listener", OnReceive)

    Parameters:
        1. conversation_name:str: the name of the IPFS port forwarding proto (IPFS connection instance)
        2. peerID:str: the IPFS peer ID of the node to communicate with
        3. others_req_listener:str: the name of the ther peer's conversation listener object
        4. file_eventhandler:function (filepath:str, metadata:bytearray): function to be called when a file is receive over this conversation
        5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
        6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
        7. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        8. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached
        9. dir:str: the path where received files should be downloaded to
    Returns:
        A Conversation object through which messages and files can be sent
    """
    conv = Conversation()
    conv.Start(conversation_name,
               peerID,
               others_req_listener,
               data_received_eventhandler,
               file_eventhandler=file_eventhandler,
               file_progress_callback=file_progress_callback,
               encryption_callbacks=encryption_callbacks,
               transmission_send_timeout_sec=transmission_send_timeout_sec,
               transmission_request_max_retries=transmission_request_max_retries,
               dir=dir
               )
    return conv


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
            conv.Join(conversation_name, peerID,
                      conversation_name, OnMessageReceived)
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
        # Conversation Initiator:
        def OnReceive(conversation, data):
            print(data.decode("utf-8"))

        conversation = Conversation()
        conversation.Start("test", "QmHash", "conv listener", OnReceive)
        conversation.Say("Hello there!".encode())

        # The other peer must have a conversation listener named "conv listener" running, e.g. via:
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
    peerID = ""
    # file_progress_callback = None
    data_received_eventhandler = None
    file_eventhandler = None
    file_progress_callback = None
    _transmission_send_timeout_sec = transmission_send_timeout_sec
    _transmission_request_max_retries = transmission_request_max_retries
    listener = None
    __encryption_callback = None
    __decryption_callback = None
    _terminate = False

    last_coms_time = None

    def __init__(self):
        self.started = Event()
        self.conversation_started = False
        self.data_received_eventhandler = None
        self.file_eventhandler = None
        self.file_progress_callback = None
        self.message_queue = Queue()
        self.file_queue = Queue()

    def Start(self,
              conversation_name,
              peerID,
              others_req_listener,
              data_received_eventhandler=None,
              file_eventhandler=None,
              file_progress_callback=None,
              encryption_callbacks=None,
              transmission_send_timeout_sec=transmission_send_timeout_sec,
              transmission_request_max_retries=transmission_request_max_retries,
              dir="."
              ):
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
            1. conversation_name:str: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID:str: the IPFS peer ID of the node to communicate with
            3. others_req_listener:str: the name of the ther peer's conversation listener object
            4. file_eventhandler:function (filepath:str, metadata:bytearray): function to be called when a file is receive over this conversation
            5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
            6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
            7. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
            8. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached
            9. dir:str: the path where received files should be downloaded to
        Returns:
            bool success: whether or not the conversation with the peer was successfully started
        """
        if peerID == IPFS_API.MyID():
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as your conversation partner.")
        if(print_log_conversations):
            print(conversation_name + ": Starting conversation")
        self.conversation_name = conversation_name
        self.data_received_eventhandler = data_received_eventhandler
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback
        if encryption_callbacks:
            self.__encryption_callback = encryption_callbacks[0]
            self.__decryption_callback = encryption_callbacks[1]
        self._transmission_send_timeout_sec = transmission_send_timeout_sec
        self._transmission_request_max_retries = transmission_request_max_retries
        self.peerID = peerID
        if print_log_conversations:
            print(conversation_name + ": sending conversation request")
        self.listener = ListenForTransmissions(conversation_name,
                                               self.Hear
                                               )
        self.file_listener = ListenForFileTransmissions(
            f"{conversation_name}:files",
            self.FileReceived,
            progress_handler=self.OnFileProgressReceived,
            dir=dir,
            encryption_callbacks=encryption_callbacks
        )
        # self.listener = ListenForTransmissions(conversation_name, self.hear_eventhandler)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        TransmitData(data,
                     peerID,
                     others_req_listener,
                     self._transmission_send_timeout_sec,
                     self._transmission_request_max_retries
                     )
        self.last_coms_time = datetime.utcnow()
        if print_log_conversations:
            print(conversation_name + ": sent conversation request")
        self.started.wait()
        return True     # signal success

    def Join(self,
             conversation_name,
             peerID,
             others_trsm_listener,
             data_received_eventhandler=None,
             file_eventhandler=None,
             file_progress_callback=None,
             encryption_callbacks=None,
             transmission_send_timeout_sec=transmission_send_timeout_sec,
             transmission_request_max_retries=transmission_request_max_retries,
             dir="."):
        """
        Joins a conversation which another peer started, given their peer ID
        and conversation's transmission-listener's name.
        Used by a conversation listener. See ListenForConversations for usage.
        Parameters:
            1. conversation_name:str: the name of the IPFS port forwarding proto (IPFS connection instance)
            2. peerID:str: the IPFS peer ID of the node to communicate with
            3. others_trsm_listener:str: the name of the other peer's conversation listener object
            4. file_eventhandler:function (filepath:str, metadata:bytearray): function to be called when a file is receive over this conversation
            5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
            6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
            7. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
            8. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached
            9. dir:str: the path where received files should be downloaded to
        Returns:
            bool success: whether or not the conversation with the peer was successfully joined
        """
        self.conversation_name = conversation_name
        if print_log_conversations:
            print(conversation_name + ": Joining conversation "
                  + others_trsm_listener)
        self.data_received_eventhandler = data_received_eventhandler
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback
        if encryption_callbacks:
            self.__encryption_callback = encryption_callbacks[0]
            self.__decryption_callback = encryption_callbacks[1]
        self._transmission_send_timeout_sec = transmission_send_timeout_sec
        self._transmission_request_max_retries = transmission_request_max_retries
        self.listener = ListenForTransmissions(conversation_name,
                                               self.Hear,
                                               )
        self.file_listener = ListenForFileTransmissions(
            f"{conversation_name}:files", self.FileReceived,
            progress_handler=self.OnFileProgressReceived,
            dir=dir,
            encryption_callbacks=encryption_callbacks
        )

        self.others_trsm_listener = others_trsm_listener
        self.peerID = peerID
        data = bytearray("I'm listening".encode(
            'utf-8')) + bytearray([255]) + bytearray(conversation_name.encode('utf-8'))
        self.conversation_started = True
        TransmitData(data, peerID, others_trsm_listener)
        self.last_coms_time = datetime.utcnow()
        if print_log_conversations:
            print(conversation_name + ": Joined conversation "
                  + others_trsm_listener)
        return True  # signal success

    def Hear(self, data, peerID, arg3=""):
        """
        Receives data from the conversation.
        Forwards it to the user's data_received_eventhandler if the conversation has already started,
        otherwise processes the converation initiation codes.
        """
        if self._terminate:
            return
        # print("HEAR", data)
        if not data:
            print("CONV.HEAR: RECEIVED NONE")
            return
        self.last_coms_time = datetime.utcnow()

        if not self.conversation_started:
            info = SplitBy255(data)
            if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
                self.others_trsm_listener = info[1].decode('utf-8')
                # self.hear_eventhandler = self.Hear
                self.conversation_started = True
                if print_log_conversations:
                    print(self.conversation_name +
                          ": peer joined, conversation started")
                self.started.set()

            elif print_log_conversations:
                print(self.conversation_name +
                      ": received unrecognisable buffer, expected join confirmation")
                print(info[0])
            return
        else:   # conversation has already started
            if self.__decryption_callback:
                if print_log_conversations:
                    print("Conv.Hear: decrypting message")
                data = self.__decryption_callback(data)
            self.message_queue.put(data)

            if self.data_received_eventhandler:
                # if the data_received_eventhandler has 2 parameters
                if len(signature(self.data_received_eventhandler).parameters) == 2:
                    Thread(target=self.data_received_eventhandler,
                           args=(self, data), name="Converstion.data_received_eventhandler").start()
                else:
                    Thread(target=self.data_received_eventhandler, args=(
                        self, data, arg3), name="Converstion.data_received_eventhandler").start()

    def Listen(self, timeout=None):
        """Waits until the conversation peer sends a message,
            then returns that message.
        Can be used as an alternative to specifying an data_received_eventhandler
            to process received messages, or in parallel.
        Parameters:
            int timeout: how many seconds to wait until giving up and
                            returning None or raising an exception
            bool timeout_exception: whether to raise an exception or
                            quietly return None when timeout is reached.
        """
        if self._terminate:
            return
        if not timeout:
            data = self.message_queue.get()
        else:
            try:
                data = self.message_queue.get(timeout=timeout)
            except:  # timeout reached
                raise ListenTimeout("Didn't receive any data.")

        if data:
            return data
        else:
            if print_log_conversations:
                print("Conv.Listen: received nothing restarting Event Wait")
            self.Listen()

    def FileReceived(self, peer, filepath, metadata):
        self.last_coms_time = datetime.utcnow()

        if print_log_conversations:
            print(f"{self.conversation_name}: Received file: ", filepath)
        self.file_queue.put({'filepath': filepath, 'metadata': metadata})
        if self.file_eventhandler:
            Thread(target=self.file_eventhandler, args=(self, filepath, metadata),
                   name='Conversation.file_eventhandler').start()

    def ListenForFile(self, abs_timeout=None, no_coms_timeout=None, timeout_exception=False):
        """
        Parameters:
            int abs_timeout: how many seconds to wait for file reception to 
                finish until giving up and returning None or raising an exception
            int no_coms_timeout: how many seconds of no signal from peer
                until giving up and returning None or raising an exception
            bool timeout_exception: whether to raise an exception or
               quietly return None when timeout is reached.
        """
        start_time = datetime.utcnow()
        if not (abs_timeout or no_coms_timeout):    # if no timeouts are specified
            data = self.file_queue.get()
        else:   # timeouts are specified
            while True:
                # calculate timeouts relative to current time
                if no_coms_timeout:
                    # time left till next coms timeout check
                    _no_coms_timeout = no_coms_timeout - \
                        (datetime.utcnow() - self.last_coms_time).total_seconds()
                if abs_timeout:
                    # time left till absolute timeout would be reached
                    _abs_timeout = abs_timeout - \
                        (datetime.utcnow() - start_time).total_seconds()

                # Choose the timeout we need to wait for
                timeout = None
                if not abs_timeout:
                    timeout = _no_coms_timeout
                elif not no_coms_timeout:
                    timeout = _abs_timeout
                else:
                    timeout = min(_no_coms_timeout, _abs_timeout)
                try:
                    data = self.file_queue.get(timeout=timeout)
                    break
                except QueueEmpty:  # qeue timeout reached
                    # check if any of the user's timeouts were reached
                    if abs_timeout and (datetime.utcnow() - start_time).total_seconds() > abs_timeout:
                        raise ListenTimeout("Didn't receive any files.")
                    elif (datetime.utcnow() - self.last_coms_time).total_seconds() > no_coms_timeout:
                        raise CommunicationTimeout(
                            "Communication timeout reached while waiting for file.")
        if data:
            return data
        else:
            if print_log_conversations:
                print("Conv.FileListen: received nothign restarting Event Wait")
            self.ListenForFile(timeout)

    def OnFileProgressReceived(self, peerID: str, filename: str, filesize: str, progress):
        self.last_coms_time = datetime.utcnow()
        if self.file_progress_callback:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(target=CallProgressCallBack,
                   args=(self.file_progress_callback,
                         peerID,
                         filename,
                         filesize,
                         progress),
                   name='Conversation.progress_handler'
                   ).start()

            # if len(signature(self.progress_handler).parameters) == 1:
            #     self.file_progress_callback(progress)
            # elif len(signature(self.progress_handler).parameters) == 2:
            #     self.file_progress_callback(filename, progress)
            # elif len(signature(self.progress_handler).parameters) == 3:
            #     self.file_progress_callback(
            #         filename, filesize, progress)

    def Say(self,
            data,
            timeout_sec=_transmission_send_timeout_sec,
            max_retries=_transmission_request_max_retries
            ):
        """
        Transmits the input data (a bytearray of any length) to the other computer in this conversation.

        Usage:
            # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes
            success = conv.Say("data to transmit".encode(
                "utf-8"), "Qm123456789", "applicationNo2")

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
        if self.__encryption_callback:
            if print_log_conversations:
                print("Conv.Say: encrypting message")
            data = self.__encryption_callback(data)
        TransmitData(data, self.peerID, self.others_trsm_listener,
                     timeout_sec, max_retries)
        self.last_coms_time = datetime.utcnow()
        return True

    def TransmitFile(self,
                     filepath,
                     metadata=bytearray(),
                     progress_handler=file_progress_callback,
                     block_size=def_block_size,
                     transmission_send_timeout_sec=_transmission_send_timeout_sec,
                     transmission_request_max_retries=_transmission_request_max_retries
                     ):
        """
        Transmits the given file to the other computer in this conversation.
        """
        while not self.conversation_started:
            if print_log:
                print("Wanted to say something but conversation was not yet started")
            time.sleep(0.01)
        if print_log_conversations:
            print("Transmitting file to ",
                  f"{self.others_trsm_listener}:files")

        def ProgressHandler(peerID: str, filename: str, filesize: str, progress):
            self.last_coms_time = datetime.utcnow()
            if progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(target=CallProgressCallBack,
                       args=(progress_handler,
                             peerID,
                             filename,
                             filesize,
                             progress),
                       name='Conversation.progress_handler'
                       ).start()
        return TransmitFile(
            filepath,
            self.peerID,
            f"{self.others_trsm_listener}:files",
            metadata,
            ProgressHandler,
            encryption_callbacks=(self.__encryption_callback,
                                  self.__decryption_callback),
            block_size=block_size,
            transmission_send_timeout_sec=transmission_send_timeout_sec,
            transmission_request_max_retries=transmission_request_max_retries)

    def Terminate(self):
        self._terminate = True
        if self.listener:
            self.listener.Terminate()
        if self.file_listener:
            self.file_listener.Terminate()

    def Close(self):
        self.Terminate()

    def Close(self):
        self.Terminate()

    def __del__(self):
        self.Terminate()


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
            conv.Join(conversation_name, peerID,
                      conversation_name, OnMessageReceived)
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
            print(
                f"ConvLisReceived {self.listener_name}: Received Conversation Request")
        info = SplitBy255(data)
        if info[0] == bytearray("I want to start a conversation".encode('utf-8')):
            if print_log_conversations:
                print(
                    f"ConvLisReceived {self.listener_name}: Starting conversation...")
            conversation_name = info[1].decode('utf-8')
            self.eventhandler(conversation_name, peerID)
        elif print_log_conversations:
            print(
                f"ConvLisReceived {self.listener_name}: Received unreadable request")
            print(info[0])

    def Terminate(self):
        self.listener.Terminate()

    def __del__(self):
        self.Terminate()


def TransmitFile(filepath,
                 peerID,
                 others_req_listener,
                 metadata=bytearray(),
                 progress_handler=None,
                 encryption_callbacks=None,
                 block_size=def_block_size,
                 transmission_send_timeout_sec=transmission_send_timeout_sec,
                 transmission_request_max_retries=transmission_request_max_retries
                 ):
    """Transmits the given file to the specified peer
    Usage:
        transmitter = TransmitFile(
            "text.txt", "QMHash", "my_apps_filelistener", "testmeadata".encode())
    Paramaters:
        1. filepath:str: the path of the file to transmit
        2. peerID:str: the IPFS peer ID of the node to communicate with
        3. others_req_listener:str: the name of the other peer's file listener object
        4. metadata:bytearray: optional metadata to send to the receiver
        5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
        6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
        7. block_size:int: the FileTransmitter sends the file in chunks. This is the siize of those chunks in bytes (default 1MiB)
        8. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        9. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached

    Returns:
        FileTransmitter file_transmitter: returned only if the transmission starts successfully
    """
    file_transmitter = FileTransmitter(
        filepath,
        peerID,
        others_req_listener,
        metadata=metadata,
        progress_handler=progress_handler,
        encryption_callbacks=encryption_callbacks,
        block_size=block_size,
        transmission_send_timeout_sec=transmission_send_timeout_sec,
        transmission_request_max_retries=transmission_request_max_retries
    )
    success = file_transmitter.Start()
    if success:
        return file_transmitter


def ListenForFileTransmissions(listener_name,
                               eventhandler,
                               progress_handler=None,
                               dir=".",
                               encryption_callbacks=None):
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
    Parameters:
        1. listener_name:str: name of this listener object, used by file sender to adress this listener
        2.  eventhandler:function(peerID:str, path:str, metadata:bytes):
                            function to be called when a file is received
        3. progress_handler:function(peerID:str, filesize:int, progress:float):
                            function to be called whenever a block of data
                            is received during an ongoing file transmission.
                            progress is a value between 0 and 1
        4. dir:str: the directory in which received files should be written
        5. encryption_callbacks:Tuple(
                                        function(plaintext:bytearray):bytearray,
                                        function(cipher:str):bytearray
                                    ):
                            encryption and decryption functions
    """
    def RequestHandler(conv_name, peerID):
        ft = FileTransmissionReceiver()
        conv = Conversation()
        ft.Setup(conv, eventhandler, progress_handler=progress_handler, dir=dir)
        conv.Join(conv_name,
                  peerID,
                  conv_name,
                  ft.OnDataReceived,
                  encryption_callbacks=encryption_callbacks
                  )

    return ConversationListener(listener_name, RequestHandler)


class FileTransmitter:
    """Transmits the given file to the specified peer
    Usage:
        file_transmitter = FileTransmitter(
            "text.txt", "QMHash", "filelistener", "testmeadata".encode())
        file_transmitter.Start()
    Paramaters:
        1. filepath:str: the path of the file to transmit
        2. peerID:str: the IPFS peer ID of the node to communicate with
        3. others_req_listener:str: the name of the other peer's file listener object
        4. metadata:bytearray: optional metadata to send to the receiver
        5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
        6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
        7. block_size:int: the FileTransmitter sends the file in chunks. This is the siize of those chunks in bytes (default 1MiB)
        8. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        9. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached
    Returns:
        FileTransmitter file_transmitter: returned only if the transmission starts successfully
    """
    status = "not started"  # "transitting" "finished" "aborted"

    def __init__(self,
                 filepath,
                 peerID,
                 others_req_listener,
                 metadata=bytearray(),
                 progress_handler=None,
                 encryption_callbacks=None,
                 block_size=def_block_size,
                 transmission_send_timeout_sec=transmission_send_timeout_sec,
                 transmission_request_max_retries=transmission_request_max_retries
                 ):
        """
        Paramaters:
            1. filepath:str: the path of the file to transmit
            2. peerID:str: the IPFS peer ID of the node to communicate with
            3. others_req_listener:str: the name of the other peer's file listener object
            4. metadata:bytearray: optional metadata to send to the receiver
            5. progress_handler:function(progress:float): eventhandler to send progress (fraction twix 0-1) every for sending/receiving files
            6. encryption_callbacks:Tuple(function(plaintext:bytearray):bytearray, function(cipher:str):bytearray): encryption and decryption functions
            7. block_size:int: the FileTransmitter sends the file in chunks. This is the siize of those chunks in bytes (default 1MiB)
            8. transmission_send_timeout_sec:int: (low level) data transmission - connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
            9. transmission_request_max_retries:int: (low level) data transmission - how often the transmission should be reattempted when the timeout is reached
        Returns:
            FileTransmitter file_transmitter: returned only if the transmission starts successfully
        """
        if peerID == IPFS_API.MyID():
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as the recipient.")
        self.filename = os.path.basename(filepath)
        self.filesize = os.path.getsize(filepath)
        self.filepath = filepath
        self.peerID = peerID
        self.others_req_listener = others_req_listener
        self.metadata = metadata
        self.progress_handler = progress_handler
        self.encryption_callbacks = encryption_callbacks
        self.block_size = block_size
        self._transmission_send_timeout_sec = transmission_send_timeout_sec
        self._transmission_request_max_retries = transmission_request_max_retries

    def Start(self):
        """
        Returns:
            bool success: whether or not file transmission was successfully started
        """
        self.conv_name = self.filename + "_conv"
        self.conversation = Conversation()
        self.conversation.Start(
            self.conv_name,
            self.peerID,
            self.others_req_listener,
            data_received_eventhandler=self.Hear,
            encryption_callbacks=self.encryption_callbacks,
            transmission_send_timeout_sec=self._transmission_send_timeout_sec,
            transmission_request_max_retries=self._transmission_request_max_retries
        )
        self.conversation.Say(
            ToB255No0s(self.filesize) + bytearray([255])
            + bytearray(self.filename.encode()) + bytearray([255]) + self.metadata)
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": Sent transmission request")
        self.CallProgressCallBack(0)
        return True

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
                self.CallProgressCallBack(position / self.filesize,)

                if print_log_files:
                    print("FileTransmission: " + self.filename
                          + ": sending data " + str(position) + "/" + str(self.filesize))
                self.conversation.Say(data)
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": finished file transmission")
        self.status = "finished"
        self.conversation.Close()

    def CallProgressCallBack(self, progress):
        if self.progress_handler:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(target=CallProgressCallBack,
                   args=(self.progress_handler,
                         self.peerID,
                         self.filename,
                         self.filesize,
                         progress),
                   name='Conversation.progress_handler'
                   ).start()
            # if len(signature(self.progress_handler).parameters) == 1:
            #     Thread(target=self.progress_handler, args=(progress,),
            #            name='Conversation.progress_handler').start()
            # elif len(signature(self.progress_handler).parameters) == 2:
            #     Thread(target=self.progress_handler, args=(self.filename, progress),
            #            name='Conversation.progress_handler').start()
            # elif len(signature(self.progress_handler).parameters) == 3:
            #     Thread(target=self.progress_handler,
            #            args=(self.filename, self.filesize, progress), name='Conversation.progress_handler').start()

    def Hear(self, conv, data):
        if print_log_files:
            print("FileTransmission: " + self.filename
                  + ": received response from receiver")
        info = SplitBy255(data)
        if info[0].decode('utf-8') == "ready":
            self.StartTransmission()

    def __del__(self):
        if self.conversation:
            self.conversation.Close()


class FileTransmissionReceiver:
    transmission_started = False
    writtenbytes = 0
    status = "not started"  # "receiving" "finished" "aborted"

    def Setup(self, conversation, eventhandler, progress_handler=None, dir="."):
        """
        Parameters:
            Conversation conversation: the Conversation object with which to
                                        communicate with the transmitter
            function(peerID:str, path:str, metadata:bytes) eventhandler:
                                function to be called when a file is received
            function(peerID:str, filesize:int, progress:float) progress_handler:
                                function to be called whenever a block of data
                                is received during an ongoing file transmission.
                                progress is a value between 0 and 1

        """
        if print_log_files:
            print("FileReception: "
                  + ": Preparing to receive file")

        self.eventhandler = eventhandler
        self.progress_handler = progress_handler
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
                self.writer = open(os.path.join(
                    self.dir, self.filename + ".PART"), "wb")
                self.transmission_started = True
                self.conv.Say("ready".encode())
                self.writtenbytes = 0
                if print_log_files:
                    print("FileReception: " + self.filename
                          + ": ready to receive file")
                if self.progress_handler:
                    # run callback on a new thread, specifying only as many parameters as the callback wants
                    Thread(target=CallProgressCallBack,
                           args=(self.progress_handler,
                                 self.conv.peerID,
                                 self.filename,
                                 self.filesize,
                                 0
                                 ),
                           name='FileTransmissionReceiver.progress'
                           ).start()

                if(self.filesize == 0):
                    self.Finish()
            except:
                if print_log_files:
                    print("Received unreadable data on FileTransmissionListener ")
                    traceback.print_exc()

        else:
            self.writer.write(data)
            self.writtenbytes += len(data)

            if self.progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(target=CallProgressCallBack,
                       args=(self.progress_handler,
                             self.conv.peerID,
                             self.filename,
                             self.filesize,
                             self.writtenbytes / self.filesize
                             ),
                       name='FileTransmissionReceiver.progress'
                       ).start()

            if print_log_files:
                print("FileTransmission: " + self.filename
                      + ": received data " + str(self.writtenbytes) + "/" + str(self.filesize))

            if self.writtenbytes == self.filesize:
                self.Finish()
            elif self.writtenbytes > self.filesize:
                self.writer.close()
                raise UnreadableReply(
                    "Something weird happened, filesize is larger than expected.")

    def Finish(self):
        self.writer.close()
        shutil.move(os.path.join(self.dir, self.filename + ".PART"),
                    os.path.join(self.dir, self.filename))
        if print_log:
            print("FileReception: " + self.filename
                  + ": Transmission finished.")
        self.status = "finished"
        self.conv.Close()
        if self.eventhandler:
            filepath = os.path.abspath(os.path.join(
                self.dir, self.filename))
            if signature(self.eventhandler).parameters["metadata"]:
                self.eventhandler(self.conv.peerID, filepath, self.metadata)
            else:
                self.eventhandler(self.conv.peerID, filepath)

    def Terminate(self):
        self.conv.Terminate()


def CallProgressCallBack(callback, peerID, filename, filesize, progress):
    """Calls the specified callback function with part of all of the rest of
    the parameters, depending on how many parameters the callback takes.
    The callback can take between 1 and 4 parameters"""
    if len(signature(callback).parameters) == 1:
        callback(progress)
    elif len(signature(callback).parameters) == 2:
        callback(filename, progress)
    elif len(signature(callback).parameters) == 3:
        callback(filename, filesize, progress)
    elif len(signature(callback).parameters) == 4:
        callback(peerID, filename, filesize, progress)


# ----------IPFS Technicalitites-------------------------------------------
connections_send = list()
connections_listen = list()


def CreateSendingConnection(peerID: str, protocol: str, port=None):
    IPFS_API.ClosePortForwarding(
        targetaddress="/p2p/" + peerID, protocol="/x/" + protocol)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if port == None:
        for prt in sending_ports:   # trying ports until we find a free one
            try:
                IPFS_API.ForwardFromPortToPeer(protocol, prt, peerID)
                sock.connect(("127.0.0.1", prt))
                return sock
            except Exception as e:   # ignore errors caused by port already in use
                if not "bind: address already in use" in str(e):
                    raise IPFS_Error(str(e))
        raise IPFS_Error("Failed to find free port for sending connection")
    else:
        try:
            IPFS_API.ForwardFromPortToPeer(protocol, port, peerID)
            sock.connect(("127.0.0.1", prt))
            return sock
        except:
            raise IPFS_Error(str(e))


def CreateListeningConnectionTCP(protocol, port, force=True):
    """
    Parameters:
        bool force: whether or not already existing conflicting connections should be closed.
    """
    try:
        IPFS_API.ListenOnPort(protocol, port)
        if print_log_connections:
            print(f"listening as \"{protocol}\" on {port}")
    except Exception as e:
        if force:
            IPFS_API.ClosePortForwarding(
                listenaddress=f"/ip4/127.0.0.1/tcp/{port}")
            IPFS_API.ClosePortForwarding(protocol=f"/x/{protocol}")
        try:
            IPFS_API.ListenOnPort(protocol, port)
        except:
            raise IPFS_Error(
                "Error registering listening connection to IPFS: /x/" + protocol + "/ip4/127.0.0.1/tcp/" + str(port))
    connections_listen.append((protocol, port))
    return port


def CreateListeningConnection(protocol, port, force=True):
    """
    Parameters:
        bool force: whether or not already existing conflicting connections should be closed.
    """
    try:
        IPFS_API.ListenOnPort(protocol, port)
        if print_log_connections:
            print(f"listening fas \"{protocol}\" on {port}")
    except Exception as e:
        if force:
            IPFS_API.ClosePortForwarding(
                listenaddress=f"/ip4/127.0.0.1/udp/{port}")
            IPFS_API.ClosePortForwarding(protocol=f"/x/{protocol}")
        try:
            time.sleep(0.1)
            IPFS_API.ListenOnPort(protocol, port)
            if print_log_connections:
                print(f"listening fas \"{protocol}\" on {port}")
        except:
            raise IPFS_Error(
                "Error registering listening connection to IPFS: /x/" + protocol + "/ip4/127.0.0.1/udp/" + str(port))

    connections_listen.append((protocol, port))
    return port


def CloseSendingConnection(peerID, protocol):
    try:
        IPFS_API.ClosePortForwarding(
            targetaddress="/p2p/" + peerID, protocol=f"/x/{protocol}")
    except Exception as e:
        raise IPFS_Error(str(e))


def CloseListeningConnection(protocol, port):
    try:
        IPFS_API.ClosePortForwarding(
            protocol=f"/x/{protocol}", targetaddress=f"/ip4/127.0.0.1/tcp/{port}")
    except Exception as e:
        raise IPFS_Error(str(e))


def ListenToBuffers(eventhandler,
                    proto,
                    buffer_size=def_buffer_size,
                    monitoring_interval=2,
                    status_eventhandler=None,
                    eventhandlers_on_new_threads=True):
    return BufferReceiver(
        eventhandler,
        proto,
        buffer_size=buffer_size,
        monitoring_interval=monitoring_interval,
        status_eventhandler=status_eventhandler,
        eventhandlers_on_new_threads=eventhandlers_on_new_threads
    )


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

    def Terminate(self):
        CloseSendingConnection(self.peerID, self.proto)

    def __del__(self):
        self.Terminate()


class BufferReceiver():
    def __init__(self,
                 eventhandler,
                 proto,
                 buffer_size=def_buffer_size,
                 monitoring_interval=2,
                 status_eventhandler=None,
                 eventhandlers_on_new_threads=True):
        self.proto = proto
        self.listener = ListenerTCP(
            eventhandler,
            0,
            buffer_size=buffer_size,
            monitoring_interval=monitoring_interval,
            status_eventhandler=status_eventhandler,
            eventhandlers_on_new_threads=eventhandlers_on_new_threads
        )
        CreateListeningConnection(proto, self.listener.port)

    def Terminate(self):
        CloseListeningConnection(self.proto, self.listener.port)
        self.listener.Terminate()

    def __del__(self):
        self.Terminate()


def SendBufferToPort(buffer, addr, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(buffer, (addr, port))


class ListenerTCP(threading.Thread):
    """
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        listener = Listener(eventhandler, 0, 2048)
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

    def __init__(self,
                 eventhandler,
                 port=0,
                 buffer_size=def_buffer_size,
                 monitoring_interval=2,
                 status_eventhandler=None,
                 eventhandlers_on_new_threads=True):
        threading.Thread.__init__(self)
        self.port = port
        self.name = f"TCPListener-{port}"
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size
        self.eventhandlers_on_new_threads = eventhandlers_on_new_threads
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        self.sock.bind(("127.0.0.1", self.port))
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]

        if status_eventhandler != None:
            self.status_eventhandler = status_eventhandler
            self.monitoring_interval = monitoring_interval
            self.last_time_recv = datetime.utcnow()
            self.status_monitor_thread = Thread(
                target=self.StatusMonitor, args=(), name='ListenerTP.status_monitor').start()

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
                if self.eventhandlers_on_new_threads:
                    ev = Thread(target=self.eventhandler, args=(
                        data, ), name="TCPListener-eventhandler")
                    ev.start()
                else:
                    self.eventhandler(data)
        conn.close()
        self.sock.close()
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
        # SendBufferToPort("end".encode(), "127.0.0.1", self.port)
        self.sock.close()

    def __del__(self):
        self.Terminate()


def ListenToBuffersOnPort(eventhandler, port=0, buffer_size=def_buffer_size, monitoring_interval=2, status_eventhandler=None):
    return BufferReceiver(eventhandler, port, buffer_size, monitoring_interval, status_eventhandler)


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


def recv_timeout(the_socket, timeout=2):
    # make socket non blocking
    the_socket.setblocking(0)

    # total data partwise in an array
    total_data = bytearray()
    data = bytearray()

    # beginning time
    begin = time.time()
    while 1:
        # if you got some data, then break after timeout
        if len(total_data) > 0 and time.time() - begin > timeout:
            break

        # if you got no data at all, wait a little longer, twice the timeout
        elif time.time() - begin > timeout * 2:
            break

        # recv something
        try:
            data = the_socket.recv(def_buffer_size)
            if data:
                total_data += data
                # change the beginning time for measurement
                begin = time.time()
            # else:
            #     # sleep for sometime to indicate a gap
            #     time.sleep(0.1)
        except:
            pass

    # print("RECEIVED", type(total_data), total_data)
    return total_data
