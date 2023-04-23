"""
This is a module that enables the user to transmit and receive transmissions of data over the Interplanetary File System's P2P network (libp2p).
To use it you must have IPFS running on your computer.
Configure IPFS to enable all this:
ipfs config --json Experimental.Libp2pStreamMounting true
"""
# from pdb import set_trace as debug
import shutil
from queue import Queue, Empty as QueueEmpty
import socket
import threading
from threading import Thread, Event
from datetime import datetime
import time
import traceback
import os
# import inspect
from inspect import signature
try:
    import ipfs_api
except:
    import IPFS_API_Remote_Client as ipfs_api


# -------------- Settings ---------------------------------------------------------------------------------------------------
PRINT_LOG = False  # whether or not to print debug in output terminal
PRINT_LOG_CONNECTIONS = False
PRINT_LOG_TRANSMISSIONS = False
PRINT_LOG_CONVERSATIONS = False
PRINT_LOG_FILES = True

if not PRINT_LOG:
    PRINT_LOG_CONNECTIONS = False
    PRINT_LOG_TRANSMISSIONS = False
    PRINT_LOG_CONVERSATIONS = False
    PRINT_LOG_FILES = False


TRANSM_REQ_MAX_RETRIES = 3
TRANSM_SEND_TIMEOUT_SEC = 10
TRANSM_RECV_TIMEOUT_SEC = 10

BUFFER_SIZE = 4096  # the communication buffer size
# the size of the chunks into which files should be split before transmission
BLOCK_SIZE = 1048576    # 1MiB

sending_ports = [x for x in range(20001, 20500)]

# -------------- User Functions ----------------------------------------------------------------------------------------------


def transmit_data(
        data: bytes,
        peer_id: str,
        req_lis_name: str,
        timeout_sec: int = TRANSM_SEND_TIMEOUT_SEC,
        max_retries: int = TRANSM_REQ_MAX_RETRIES):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified IPFS peer ID.
    Args:
        data (bytearray): the data to be transmitted to the receiver
        string peer_id (str): the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name (str): the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        transm_send_timeout_sec (int): connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
        transm_req_max_retries (int): how often the transmission should be reattempted when the timeout is reached
    Returns:
        bool: whether or not the transmission succeeded
    """
    if peer_id == ipfs_api.my_id():
        raise InvalidPeer(
            message="You cannot use your own IPFS peer ID as the recipient.")

    def SendTransmissionRequest():
        """
        Sends transmission request to the recipient.
        """
        request_data = __add_integritybyte_to_buffer(ipfs_api.my_id().encode())
        tries = 0

        # repeatedly try to send transmission request to recipient until a reply is received
        while max_retries == -1 or tries < max_retries:
            if PRINT_LOG_TRANSMISSIONS:
                print("Sending transmission request to " + str(req_lis_name))
            sock = _create_sending_connection(peer_id, req_lis_name)
            # sock.sendall(request_data)
            sock.settimeout(timeout_sec)
            _tcp_send_all(sock, request_data)
            if PRINT_LOG_TRANSMISSIONS:
                print("Sent transmission request to " + str(req_lis_name))

            try:
                # reply = sock.recv(BUFFER_SIZE)
                reply = _tcp_recv_buffer_timeout(sock, BUFFER_SIZE,
                                                 timeout=timeout_sec)
            except socket.timeout:
                sock.close()
                _close_sending_connection(peer_id, req_lis_name)
                raise CommunicationTimeout(
                    "Received no response from peer while sending transmission request.")

            # reply = _tcp_recv_all(sock, timeout_sec)
            # _tcp_recv_all
            sock.close()
            del sock
            _close_sending_connection(peer_id, req_lis_name)
            if reply:
                try:
                    their_trsm_port = reply[30:].decode()  # signal success
                    if their_trsm_port:
                        if PRINT_LOG_TRANSMISSIONS:
                            print("Transmission request to " +
                                  str(req_lis_name) + "was received.")
                        return their_trsm_port
                    else:
                        raise UnreadableReply()
                except:
                    raise UnreadableReply()
            else:
                if PRINT_LOG_TRANSMISSIONS:
                    print("Transmission request send " +
                          str(req_lis_name) + "timeout_sec reached.")
            tries += 1
        _close_sending_connection(peer_id, req_lis_name)
        raise CommunicationTimeout(
            "Received no response from peer while sending transmission request.")

    their_trsm_port = SendTransmissionRequest()
    sock = _create_sending_connection(peer_id, their_trsm_port)
    sock.settimeout(timeout_sec)
    # sock.sendall(data)  # transmit Data
    _tcp_send_all(sock, data)
    if PRINT_LOG_TRANSMISSIONS:
        print("Sent Transmission Data", data)
    response = sock.recv(BUFFER_SIZE)
    if response and response == b"Finished!":
        # conn.close()
        sock.close()
        _close_sending_connection(peer_id, their_trsm_port)
        if PRINT_LOG_TRANSMISSIONS:
            print(": Finished transmission.")
        return True  # signal success
    else:
        if PRINT_LOG_TRANSMISSIONS:
            print("Received unrecognised response:", response)
        raise UnreadableReply()
    # sock.close()
    # _close_sending_connection(peer_id, their_trsm_port)


def listen_for_transmissions(listener_name, eventhandler):
    """
    Listens for incoming transmission requests (senders requesting to transmit
    data to us) and sets up the machinery needed to receive those transmissions.
    Call `.terminate()` on the returned TransmissionListener object when you
    no longer need it to clean up IPFS connection configurations.

    Args:
        listener_name (str): the name of this TransmissionListener (chosen by
            user, allows distinguishing multiple IPFS-DataTransmission-Listeners
            running on the same computer for different applications)
        eventhandler (function): the function that should be called when a
            transmission of data is received
            Parameters: data (bytearray), peer_id (str)
    Returns:
        TramissionListener: listener object which can be terminated with
            `.terminate()` or whose `.eventhandler` attribute can be changed.
    """
    return TransmissionListener(listener_name, eventhandler)


class TransmissionListener:
    """
    Listens for incoming transmission requests (senders requesting to transmit
    data to us) and sets up the machinery needed to receive those transmissions.
    Call `.terminate()` on  TransmissionListener objects when you no longer
    need them to clean up IPFS connection configurations.
    """
    # This function itself is called to process the transmission request buffer sent by the transmission sender.
    _terminate = False

    def __init__(self, listener_name, eventhandler):
        """
        Args:
            listener_name (str): the name of this TransmissionListener (chosen by
                user, allows distinguishing multiple IPFS-DataTransmission-Listeners
                running on the same computer for different applications)
            eventhandler (function): the function that should be called when a transmission of
                data is received.
                Parameters: data (bytearray), peer_id (str)
        """
        self._listener_name = listener_name
        self.eventhandler = eventhandler
        self._listener = Thread(target=self._listen, args=(),
                                name=f"DataTransmissionListener-{listener_name}")
        self._listener.start()

    def __receive_transmission_requests(self, data):
        if PRINT_LOG_TRANSMISSIONS:
            print(self._listener_name + ": processing transmission request...")
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
                if PRINT_LOG:
                    print(
                        self._listener_name + ": Received a buffer with a non-matching integrity buffer")
                return

            peer_id = data.decode()

            if PRINT_LOG_TRANSMISSIONS:
                print(
                    self._listener_name + ": Received transmission request.")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            our_port = sock.getsockname()[1]
            _create_listening_connection(str(our_port), our_port)
            sock.listen()

            listener = Thread(target=self._receive_transmission, args=(
                peer_id, sock, our_port, self.eventhandler), name=f"DataTransmissionReceiver-{our_port}")
            listener.start()
            return our_port

        except Exception as e:
            print("")
            print(
                self._listener_name + ": Exception in NetTerm.ReceiveTransmissions.__receive_transmission_requests()")
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print(self._listener_name + ": Could not decode transmission request.")

    def _receive_transmission(self, peer_id, sock, our_port, eventhandler):
        #
        # sock = _create_sending_connection(peer_id, str(sender_port))
        #
        # if PRINT_LOG_TRANSMISSIONS:
        #     print("Ready to receive transmission.")
        #
        # sock.sendall(b"start transmission")
        if PRINT_LOG_TRANSMISSIONS:
            print("waiting to receive actual transmission")
        conn, addr = sock.accept()
        if PRINT_LOG_TRANSMISSIONS:
            print("received connection response fro actual transmission")

        data = _tcp_recv_all(conn, timeout=TRANSM_RECV_TIMEOUT_SEC)
        conn.send("Finished!".encode())
        # conn.close()
        Thread(target=eventhandler, args=(data, peer_id),
               name="TransmissionListener.ReceivedTransmission").start()
        _close_listening_connection(str(our_port), our_port)
        sock.close()

    def _listen(self):
        if PRINT_LOG_TRANSMISSIONS:
            print("Creating Listener")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        _create_listening_connection(self._listener_name, self.port)

        if PRINT_LOG_TRANSMISSIONS:
            print(self._listener_name
                  + ": Listening for transmission requests as " + self._listener_name)
        self.socket.listen()
        while True:
            conn, addr = self.socket.accept()
            data = _tcp_recv_all(conn, timeout=TRANSM_RECV_TIMEOUT_SEC)
            if self._terminate:
                # conn.sendall(b"Righto.")
                conn.close()
                self.socket.close()
                return
            port = self.__receive_transmission_requests(data)
            if port:
                conn.send(f"Transmission request accepted.{port}".encode())
            else:
                conn.send(b"Transmission request not accepted.")

    def terminate(self):
        """Stop listening for transmissions and clean up IPFS connection
        configurations."""
        # self.socket.unbind(self.port)
        self._terminate = True
        _close_listening_connection(self._listener_name, self.port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", self.port))
            # sock.sendall("close".encode())
            _tcp_send_all(sock, "close".encode())

            # _tcp_recv_all(sock)
            sock.close()
            del sock
        except:
            pass

    def __del__(self):
        self.terminate()


def start_conversation(conv_name,
                       peer_id,
                       others_req_listener,
                       data_received_eventhandler=None,
                       file_eventhandler=None,
                       file_progress_callback=None,
                       encryption_callbacks=None,
                       timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
                       max_retries=TRANSM_REQ_MAX_RETRIES,
                       dir="."):
    """Starts a conversation object with which 2 peers can repetatively make
    data transmissions to each other asynchronously and bidirectionally.
    Sends a conversation request to the other peer's conversation request
    listener which the other peer must (programmatically) accept (joining the
    conversation) in order to start conversing.
    Call `.terminate()` on the returned Conversation object when you
    no longer need it to clean up IPFS connection configurations.
    Args:
        conv_name (str): the name of the IPFS port forwarding connection
                                (IPFS Libp2pStreamMounting protocol)
        peer_id (str): the IPFS peer ID of the node to communicate with
        others_req_listener (str): the name of the ther peer's conversation
                                listener object
        data_received_eventhandler (function): function to be called when we've
                                received a data transmission
                                Parameters: (data:bytearray)
        file_eventhandler (function): function to be called when a file is
                                receive over this conversation
                                Parameters: (filepath:str, metadata:bytearray)
        progress_handler (function): eventhandler to send progress (fraction
                                twix 0-1) every for sending/receiving files
                                Parameters: (progress:float)
        encryption_callbacks (tuple): encryption and decryption functions
                                Tuple Contents: two functions which each take a
                                a bytearray as a parameter and return a bytearray
                                (
                                    function(plaintext:bytearray):bytearray,
                                    function(cipher:bytearray):bytearray
                                )
        transm_send_timeout_sec (int): (low level) data transmission -
                                connection attempt timeout, multiplied with the
                                maximum number of retries will result in the
                                total time required for a failed attempt
        transm_req_max_retries (int): (low level) data transmission -
                                how often the transmission should be
                                reattempted when the timeout is reached
        dir (str): the path where received files should be downloaded to
    Returns:
        Conversation: an object through which messages and files can be sent
    """
    conv = Conversation()
    conv.start(conv_name,
               peer_id,
               others_req_listener,
               data_received_eventhandler,
               file_eventhandler=file_eventhandler,
               file_progress_callback=file_progress_callback,
               encryption_callbacks=encryption_callbacks,
               transm_send_timeout_sec=timeout_sec,
               transm_req_max_retries=max_retries,
               dir=dir
               )
    return conv


def join_conversation(conv_name,
                      peer_id,
                      others_req_listener,
                      data_received_eventhandler=None,
                      file_eventhandler=None,
                      file_progress_callback=None,
                      encryption_callbacks=None,
                      timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
                      max_retries=TRANSM_REQ_MAX_RETRIES,
                      dir="."):
    """Join a conversation object started by another peer.
    Call `.terminate()` on the returned Conversation object when you
    no longer need it to clean up IPFS connection configurations.
    Args:
        conv_name (str): the name of the IPFS port forwarding connection
                                (IPFS Libp2pStreamMounting protocol)
        peer_id (str): the IPFS peer ID of the node to communicate with
        others_req_listener (str): the name of the ther peer's conversation
                                listener object
        data_received_eventhandler (function): function to be called when we've
                                received a data transmission
                                Parameters: (data:bytearray)
        file_eventhandler (function): function to be called when a file is
                                receive over this conversation
                                Parameters: (filepath:str, metadata:bytearray)
        progress_handler (function): eventhandler to send progress (fraction
                                twix 0-1) every for sending/receiving files
                                Parameters: (progress:float)
        encryption_callbacks (tuple): encryption and decryption functions
                                Tuple Contents: two functions which each take a
                                a bytearray as a parameter and return a bytearray
                                (
                                    function(plaintext:bytearray):bytearray,
                                    function(cipher:bytearray):bytearray
                                )
        transm_send_timeout_sec (int): (low level) data transmission -
                                connection attempt timeout, multiplied with the
                                maximum number of retries will result in the
                                total time required for a failed attempt
        transm_req_max_retries (int): (low level) data transmission -
                                how often the transmission should be
                                reattempted when the timeout is reached
        dir (str): the path where received files should be downloaded to
    Returns:
        Conversation: an object through which messages and files can be sent
    """
    conv = Conversation()
    conv.join(conv_name,
              peer_id,
              others_req_listener,
              data_received_eventhandler,
              file_eventhandler=file_eventhandler,
              file_progress_callback=file_progress_callback,
              encryption_callbacks=encryption_callbacks,
              transm_send_timeout_sec=timeout_sec,
              transm_req_max_retries=max_retries,
              dir=dir
              )
    return conv


def listen_for_conversations(listener_name: str, eventhandler):
    """
    Listen for incoming conversation requests.
    Whenever a new conversation request is received, the specified eventhandler
    is called which must then decide whether or not to join the conversation,
    and then act upon that decision.
    Call `.terminate()` on the returned ConversationListener object when you
    no longer need it to clean up IPFS connection configurations.
    Args:
        listener_name (str): the name which this ConversationListener should
                        have (becomes its IPFS Libp2pStreamMounting protocol)
        eventhandler (function): the function to be called when a conversation
                        request is received
                        Parameters: (conv_name:str, peer_id:str)
    Returns:
        ConversationListener: an object which listens for incoming conversation
                                requests
    """
    return ConversationListener(listener_name, eventhandler)


class Conversation:
    """Communication object which allows 2 peers to repetatively make
    data transmissions to each other asynchronously and bidirectionally.
    """
    conv_name = ""
    peer_id = ""
    data_received_eventhandler = None
    file_eventhandler = None
    file_progress_callback = None
    _transm_send_timeout_sec = TRANSM_SEND_TIMEOUT_SEC
    _transm_req_max_retries = TRANSM_REQ_MAX_RETRIES
    _listener = None
    __encryption_callback = None
    __decryption_callback = None
    _terminate = False

    _last_coms_time = None

    def __init__(self):
        self.started = Event()
        self._conversation_started = False
        self.data_received_eventhandler = None
        self.file_eventhandler = None
        self.file_progress_callback = None
        self.message_queue = Queue()
        self._file_queue = Queue()

    def start(self,
              conv_name,
              peer_id,
              others_req_listener,
              data_received_eventhandler=None,
              file_eventhandler=None,
              file_progress_callback=None,
              encryption_callbacks=None,
              transm_send_timeout_sec=_transm_send_timeout_sec,
              transm_req_max_retries=_transm_req_max_retries,
              dir="."):
        """Initialises this conversation object so that it can be used.
        Code execution blocks until the other peer joins the conversation or
        timeout is reached.
        Args:
            conv_name (str): the name of the IPFS port forwarding connection
                            (IPFS Libp2pStreamMounting protocol)
            peer_id (str): the IPFS peer ID of the node to communicate with
            others_req_listener (str): the name of the ther peer's conversation
                            listener object
            data_received_eventhandler (function): function to be called when
                            we've received a data transmission
                            Parameters: (data:bytearray)
            file_eventhandler (function): function to be called when a file is
                            receive over this conversation
                            Parameters: (filepath:str, metadata:bytearray)
            progress_handler (function): eventhandler to send progress (float
                            twix 0-1) every for sending/receiving files
                            Parameters: (progress:float)
            encryption_callbacks (tuple): encryption and decryption functions
                            Tuple Contents: two functions which each take a
                            a bytearray as a parameter and return a bytearray
                            (
                                function(plaintext:bytearray):bytearray,
                                function(cipher:bytearray):bytearray
                            )
            transm_send_timeout_sec (int): (low level) data transmission
                            connection attempt timeout, multiplied with the
                            maximum number of retries will result in the
                            total time required for a failed attempt
            transm_req_max_retries (int): (low level) data
                            transmission how often the transmission should be
                            reattempted when the timeout is reached
            dir (str): the path where received files should be downloaded to
        """
        if peer_id == ipfs_api.my_id():
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as your conversation partner.")
        if(PRINT_LOG_CONVERSATIONS):
            print(conv_name + ": Starting conversation")
        self.conv_name = conv_name
        self.data_received_eventhandler = data_received_eventhandler
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback
        if encryption_callbacks:
            self.__encryption_callback = encryption_callbacks[0]
            self.__decryption_callback = encryption_callbacks[1]
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries
        self.peer_id = peer_id
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": sending conversation request")
        self._listener = listen_for_transmissions(conv_name,
                                                  self._hear
                                                  )
        self.file_listener = listen_for_file_transmissions(
            f"{conv_name}:files",
            self._file_received,
            progress_handler=self._on_file_progress_received,
            dir=dir,
            encryption_callbacks=encryption_callbacks
        )
        # self._listener = listen_for_transmissions(conv_name, self.hear_eventhandler)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conv_name.encode('utf-8'))
        try:
            transmit_data(data,
                          peer_id,
                          others_req_listener,
                          self._transm_send_timeout_sec,
                          self._transm_req_max_retries
                          )
        except Exception as e:
            self.terminate()
            raise e
        self._last_coms_time = datetime.utcnow()
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": sent conversation request")
        self.started.wait(transm_send_timeout_sec)
        return True     # signal success

    def join(self,
             conv_name,
             peer_id,
             others_trsm_listener,
             data_received_eventhandler=None,
             file_eventhandler=None,
             file_progress_callback=None,
             encryption_callbacks=None,
             transm_send_timeout_sec=_transm_send_timeout_sec,
             transm_req_max_retries=_transm_req_max_retries,
             dir="."):
        """Joins a conversation which another peer started, given their peer ID
        and conversation's transmission-listener's name.
        Used by a conversation listener.
        See listen_for_conversations for usage.
        Args:
            conv_name (str): the name of the IPFS port forwarding connection
                            (IPFS Libp2pStreamMounting protocol)
            peer_id (str): the IPFS peer ID of the node to communicate with
            others_req_listener (str): the name of the ther peer's conversation
                            listener object
            data_received_eventhandler (function): function to be called when
                            we've received a data transmission
                            Parameters: (data:bytearray)
            file_eventhandler (function): function to be called when a file is
                            receive over this conversation
                            Parameters: (filepath:str, metadata:bytearray)
            progress_handler (function): eventhandler to send progress (float
                            twix 0-1) every for sending/receiving files
                            Parameters: (progress:float)
            encryption_callbacks (tuple): encryption and decryption functions
                            Tuple Contents: two functions which each take a
                            a bytearray as a parameter and return a bytearray
                            (
                                function(plaintext:bytearray):bytearray,
                                function(cipher:bytearray):bytearray
                            )
            transm_send_timeout_sec (int): (low level) data transmission
                            connection attempt timeout, multiplied with the
                            maximum number of retries will result in the
                            total time required for a failed attempt
            transm_req_max_retries (int): (low level) data
                            transmission how often the transmission should be
                            reattempted when the timeout is reached
            dir (str): the path where received files should be downloaded to
        """
        self.conv_name = conv_name
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": Joining conversation "
                  + others_trsm_listener)
        self.data_received_eventhandler = data_received_eventhandler
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback
        if encryption_callbacks:
            self.__encryption_callback = encryption_callbacks[0]
            self.__decryption_callback = encryption_callbacks[1]
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries
        self._listener = listen_for_transmissions(conv_name,
                                                  self._hear,
                                                  )
        self.file_listener = listen_for_file_transmissions(
            f"{conv_name}:files", self._file_received,
            progress_handler=self._on_file_progress_received,
            dir=dir,
            encryption_callbacks=encryption_callbacks
        )

        self.others_trsm_listener = others_trsm_listener
        self.peer_id = peer_id
        data = bytearray("I'm listening".encode(
            'utf-8')) + bytearray([255]) + bytearray(conv_name.encode('utf-8'))
        self._conversation_started = True
        transmit_data(data, peer_id, others_trsm_listener)
        self._last_coms_time = datetime.utcnow()
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": Joined conversation "
                  + others_trsm_listener)
        return True  # signal success

    def _hear(self, data, peer_id, arg3=""):
        """
        Receives this conversation's data transmissions.
        Forwards it to the user's data_received_eventhandler if the
        conversation has already started,
        otherwise processes the conversation initiation codes.
        """
        if self._terminate:
            return
        # print("HEAR", data)
        if not data:
            print("CONV.HEAR: RECEIVED NONE")
            return
        self._last_coms_time = datetime.utcnow()

        if not self._conversation_started:
            info = _split_by_255(data)
            if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
                self.others_trsm_listener = info[1].decode('utf-8')
                # self.hear_eventhandler = self._hear
                self._conversation_started = True
                if PRINT_LOG_CONVERSATIONS:
                    print(self.conv_name +
                          ": peer joined, conversation started")
                self.started.set()

            elif PRINT_LOG_CONVERSATIONS:
                print(self.conv_name +
                      ": received unrecognisable buffer, expected join confirmation")
                print(info[0])
            return
        else:   # conversation has already started
            if self.__decryption_callback:
                if PRINT_LOG_CONVERSATIONS:
                    print("Conv._hear: decrypting message")
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

    def listen(self, timeout=None):
        """Waits until the conversation peer sends a message, then returns that
        message. Can be used as an alternative to specifying an
        data_received_eventhandler to process received messages,
        or both can be used in parallel.
        Args:
            timeout (int): how many seconds to wait until giving up and
                            raising an exception
        Returns:
            bytearray: received data
        """
        if self._terminate:
            return
        if not timeout:
            data = self.message_queue.get()
        else:
            try:
                data = self.message_queue.get(timeout=timeout)
            except:  # timeout reached
                raise ConvListenTimeout("Didn't receive any data.")

        if data:
            return data
        else:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.listen: received nothing restarting Event Wait")
            self.listen()

    def _file_received(self, peer, filepath, metadata):
        """Receives this conversation's file transmissions."""
        self._last_coms_time = datetime.utcnow()

        if PRINT_LOG_CONVERSATIONS:
            print(f"{self.conv_name}: Received file: ", filepath)
        self._file_queue.put({'filepath': filepath, 'metadata': metadata})
        if self.file_eventhandler:
            Thread(target=self.file_eventhandler, args=(self, filepath, metadata),
                   name='Conversation.file_eventhandler').start()

    def listen_for_file(self, abs_timeout=None, no_coms_timeout=None):
        """
        Args:
            abs_timeout (int): how many seconds to wait for file reception to
                finish until giving up and raising an exception
            no_coms_timeout (int): how many seconds of no signal from peer
                until giving up and returning None or raising an exception
        Returns:
            str: the path of the received file
        """
        start_time = datetime.utcnow()
        if not (abs_timeout or no_coms_timeout):    # if no timeouts are specified
            data = self._file_queue.get()
        else:   # timeouts are specified
            while True:
                # calculate timeouts relative to current time
                if no_coms_timeout:
                    # time left till next coms timeout check
                    _no_coms_timeout = no_coms_timeout - \
                        (datetime.utcnow() - self._last_coms_time).total_seconds()
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
                    data = self._file_queue.get(timeout=timeout)
                    break
                except QueueEmpty:  # qeue timeout reached
                    # check if any of the user's timeouts were reached
                    if abs_timeout and (datetime.utcnow() - start_time).total_seconds() > abs_timeout:
                        raise ConvListenTimeout("Didn't receive any files.")
                    elif (datetime.utcnow() - self._last_coms_time).total_seconds() > no_coms_timeout:
                        raise CommunicationTimeout(
                            "Communication timeout reached while waiting for file.")
        if data:
            return data
        else:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.FileListen: received nothign restarting Event Wait")
            self.listen_for_file(timeout)

    def _on_file_progress_received(self, peer_id: str, filename: str, filesize: str, progress):
        self._last_coms_time = datetime.utcnow()
        if self.file_progress_callback:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(target=call_progress_callback,
                   args=(self.file_progress_callback,
                         peer_id,
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

    def say(self,
            data,
            timeout_sec=_transm_send_timeout_sec,
            max_retries=_transm_req_max_retries
            ):
        """
        Transmits the provided data (a bytearray of any length) to this
        conversation's peer.
        Args:
            bytearray data: the data to be transmitted to the receiver
            timeout_sec: connection attempt timeout, multiplied with the
                        maximum number of retries will result in the
                        total time required for a failed attempt
            max_retries: how often the transmission should be reattempted
                        when the timeout is reached
        Returns:
            bool success: whether or not the transmission succeeded
        """
        while not self._conversation_started:
            if PRINT_LOG:
                print("Wanted to say something but conversation was not yet started")
            time.sleep(0.01)
        if self.__encryption_callback:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.say: encrypting message")
            data = self.__encryption_callback(data)
        transmit_data(data, self.peer_id, self.others_trsm_listener,
                      timeout_sec, max_retries)
        self._last_coms_time = datetime.utcnow()
        return True

    def transmit_file(self,
                      filepath,
                      metadata=bytearray(),
                      progress_handler=file_progress_callback,
                      block_size=BLOCK_SIZE,
                      transm_send_timeout_sec=_transm_send_timeout_sec,
                      transm_req_max_retries=_transm_req_max_retries
                      ):
        """
        Transmits the provided file to the other computer in this conversation.

        """
        while not self._conversation_started:
            if PRINT_LOG:
                print("Wanted to say something but conversation was not yet started")
            time.sleep(0.01)
        if PRINT_LOG_CONVERSATIONS:
            print("Transmitting file to ",
                  f"{self.others_trsm_listener}:files")

        def _progress_handler(peer_id: str, filename: str, filesize: str, progress):
            self._last_coms_time = datetime.utcnow()
            if progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(target=call_progress_callback,
                       args=(progress_handler,
                             peer_id,
                             filename,
                             filesize,
                             progress),
                       name='Conversation.progress_handler'
                       ).start()
        return transmit_file(
            filepath,
            self.peer_id,
            f"{self.others_trsm_listener}:files",
            metadata,
            _progress_handler,
            encryption_callbacks=(self.__encryption_callback,
                                  self.__decryption_callback),
            block_size=block_size,
            transm_send_timeout_sec=transm_send_timeout_sec,
            transm_req_max_retries=transm_req_max_retries)

    def terminate(self):
        """Stop the conversation and clean up IPFS connection configurations.
        """
        self._terminate = True
        if self._listener:
            self._listener.terminate()
        if self.file_listener:
            self.file_listener.terminate()

    def close(self):
        """Stop the conversation and clean up IPFS connection configurations.
        """
        self.terminate()

    def __del__(self):
        self.terminate()


class ConversationListener:
    """
    Object which listens to incoming conversation requests.
    Whenever a new conversation request is received, the specified eventhandler
    is called which must then decide whether or not to join the conversation,
    and then act upon that decision.

    """

    def __init__(self, listener_name, eventhandler):
        self._listener_name = listener_name
        if(PRINT_LOG_CONVERSATIONS):
            print("Listening for conversations as " + listener_name)
        self.eventhandler = eventhandler
        self._listener = listen_for_transmissions(
            listener_name, self._on_request_received)

    def _on_request_received(self, data, peer_id):
        if PRINT_LOG_CONVERSATIONS:
            print(
                f"ConvLisReceived {self._listener_name}: Received Conversation Request")
        info = _split_by_255(data)
        if info[0] == bytearray("I want to start a conversation".encode('utf-8')):
            if PRINT_LOG_CONVERSATIONS:
                print(
                    f"ConvLisReceived {self._listener_name}: Starting conversation...")
            conv_name = info[1].decode('utf-8')
            self.eventhandler(conv_name, peer_id)
        elif PRINT_LOG_CONVERSATIONS:
            print(
                f"ConvLisReceived {self._listener_name}: Received unreadable request")
            print(info[0])

    def terminate(self):
        """Stop listening for conversation requests and clean up IPFS
        connection configurations.
        """
        self._listener.terminate()

    def __del__(self):
        self.terminate()


def transmit_file(filepath,
                  peer_id,
                  others_req_listener,
                  metadata=bytearray(),
                  progress_handler=None,
                  encryption_callbacks=None,
                  block_size=BLOCK_SIZE,
                  transm_send_timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
                  transm_req_max_retries=TRANSM_REQ_MAX_RETRIES
                  ):
    """Transmits the provided file to the specified peer.
    Args:
        filepath (str): the path of the file to transmit
        peer_id (str): the IPFS peer ID of the node to communicate with
        others_req_listener (str): the name of the other peer's FileListener
        metadata (bytearray): optional metadata to send to the receiver
        progress_handler (function): eventhandler to send progress (fraction
                        twix 0-1) every for sending/receiving files
                        Parameters: (progress:float)
        encryption_callbacks (tuple): encryption and decryption functions
                        Tuple Contents: two functions which each take a
                        a bytearray as a parameter and return a bytearray
                        (
                            function(plaintext:bytearray):bytearray,
                            function(cipher:bytearray):bytearray
                        )
        block_size (int): the FileTransmitter sends the file in chunks. This is
                        the size of those chunks in bytes (default 1MiB).
                        Increasing this speeds up transmission but reduces the
                        frequency of progress update messages.
        transm_send_timeout_sec (int): (low level) data transmission -
                        connection attempt timeout, multiplied with the maximum
                        number of retries will result in the total time
                        required for a failed attempt
        transm_req_max_retries (int): (low level) data transmission -
                        how often the transmission should be reattempted when
                        the timeout is reached
    Returns:
        FileTransmitter: object which manages the filetransmission
    """
    return FileTransmitter(
        filepath,
        peer_id,
        others_req_listener,
        metadata=metadata,
        progress_handler=progress_handler,
        encryption_callbacks=encryption_callbacks,
        block_size=block_size,
        transm_send_timeout_sec=transm_send_timeout_sec,
        transm_req_max_retries=transm_req_max_retries
    )


def listen_for_file_transmissions(listener_name,
                                  eventhandler,
                                  progress_handler=None,
                                  dir=".",
                                  encryption_callbacks=None):
    """Listens to incoming file transmission requests.
    Whenever a file is received, the specified eventhandler is called.
    Call `.terminate()` on the returned ConversationListener object when you
    no longer need it to clean up IPFS connection configurations.
    Args:
        listener_name (str): name of this listener object, used by file sender
                            to adress this listener
        eventhandler (function): function to be called when a file is received
                            Parameters: (peer_id:str, path:str, metadata:bytes)
        progress_handler (function): function to be called whenever a block of
                            data is received during a file transmission
                            progress is a value between 0 and 1
                            Parameters:
                                (peer_id:str, filesize:int, progress:float)
        dir (str): the directory in which received files should be written
        encryption_callbacks (tuple): encryption and decryption functions
                            Tuple Contents: two functions which each take a
                            a bytearray as a parameter and return a bytearray
                            (
                                function(plaintext:bytearray):bytearray,
                                function(cipher:bytearray):bytearray
                            )
    Returns:
        ConversationListener: an object which listens for incoming file
                            requests
    """
    def request_handler(conv_name, peer_id):
        ft = FileTransmissionReceiver()
        conv = Conversation()
        ft.setup(conv, eventhandler, progress_handler=progress_handler, dir=dir)
        conv.join(conv_name,
                  peer_id,
                  conv_name,
                  ft.on_data_received,
                  encryption_callbacks=encryption_callbacks
                  )

    return ConversationListener(listener_name, request_handler)


class FileTransmitter:
    """Object for managing file transmission (sending only, not receiving)
    """
    status = "not started"  # "transmitting" "finished" "aborted"

    def __init__(self,
                 filepath,
                 peer_id,
                 others_req_listener,
                 metadata=bytearray(),
                 progress_handler=None,
                 encryption_callbacks=None,
                 block_size=BLOCK_SIZE,
                 transm_send_timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
                 transm_req_max_retries=TRANSM_REQ_MAX_RETRIES
                 ):
        """
        Args:
            filepath (str): the path of the file to transmit
            peer_id (str): the IPFS peer ID of the node to communicate with
            others_req_listener (str): the name of the other peer's FileListener
            metadata (bytearray): optional metadata to send to the receiver
            progress_handler (function): eventhandler to send progress (fraction
                            twix 0-1) every for sending/receiving files
                            Parameters: (progress:float)
            encryption_callbacks (tuple): encryption and decryption functions
                            Tuple Contents: two functions which each take a
                            a bytearray as a parameter and return a bytearray
                            (
                                function(plaintext:bytearray):bytearray,
                                function(cipher:bytearray):bytearray
                            )
            block_size (int): the FileTransmitter sends the file in chunks. This is
                            the size of those chunks in bytes (default 1MiB).
                            Increasing this speeds up transmission but reduces the
                            frequency of progress update messages.
            transm_send_timeout_sec (int): (low level) data transmission -
                            connection attempt timeout, multiplied with the maximum
                            number of retries will result in the total time
                            required for a failed attempt
            transm_req_max_retries (int): (low level) data transmission -
                            how often the transmission should be reattempted when
                            the timeout is reached
        """
        if peer_id == ipfs_api.my_id():
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as the recipient.")
        self.filename = os.path.basename(filepath)
        self.filesize = os.path.getsize(filepath)
        self.filepath = filepath
        self.peer_id = peer_id
        self.others_req_listener = others_req_listener
        self.metadata = metadata
        self.progress_handler = progress_handler
        self.encryption_callbacks = encryption_callbacks
        self.block_size = block_size
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries

        self.conv_name = self.filename + "_conv"
        self.conversation = Conversation()
        self.conversation.start(
            self.conv_name,
            self.peer_id,
            self.others_req_listener,
            data_received_eventhandler=self._hear,
            encryption_callbacks=self.encryption_callbacks,
            transm_send_timeout_sec=self._transm_send_timeout_sec,
            transm_req_max_retries=self._transm_req_max_retries
        )
        self.conversation.say(
            _to_b255_no_0s(self.filesize) + bytearray([255])
            + bytearray(self.filename.encode()) + bytearray([255]) + self.metadata)
        if PRINT_LOG_FILES:
            print("FileTransmission: " + self.filename
                  + ": Sent transmission request")
        self._call_progress_callback(0)

    def _start_transmission(self):
        if PRINT_LOG_FILES:
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
                self._call_progress_callback(position / self.filesize,)

                if PRINT_LOG_FILES:
                    print("FileTransmission: " + self.filename
                          + ": sending data " + str(position) + "/" + str(self.filesize))
                self.conversation.say(data)
        if PRINT_LOG_FILES:
            print("FileTransmission: " + self.filename
                  + ": finished file transmission")
        self.status = "finished"
        self.conversation.close()

    def _call_progress_callback(self, progress):
        if self.progress_handler:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(target=call_progress_callback,
                   args=(self.progress_handler,
                         self.peer_id,
                         self.filename,
                         self.filesize,
                         progress),
                   name='Conversation.progress_handler'
                   ).start()

    def _hear(self, conv, data):
        if PRINT_LOG_FILES:
            print("FileTransmission: " + self.filename
                  + ": received response from receiver")
        info = _split_by_255(data)
        if info[0].decode('utf-8') == "ready":
            self._start_transmission()

    def __del__(self):
        if self.conversation:
            self.conversation.close()


class FileTransmissionReceiver:
    """Object for receiving a file transmission (after a file transmission
    request hast been received and accepted)
    """
    transmission_started = False
    writtenbytes = 0
    status = "not started"  # "receiving" "finished" "aborted"

    def setup(self, conversation, eventhandler, progress_handler=None, dir="."):
        """Configure this object to make it work.
        Args:
            conversation (Conversation): the Conversation object with which to
                        communicate with the transmitter
            eventhandler (function): function to be called when a file is
                        received
                        Parameters: (peer_id:str, path:str, metadata:bytes)
            progress_handler (function): function to be called whenever a block
                        of data is received during file transmission.
                        progress is a value between 0 and 1
                        Parameters: (peer_id:str, filesize:int, progress:float)

        """
        if PRINT_LOG_FILES:
            print("FileReception: "
                  + ": Preparing to receive file")

        self.eventhandler = eventhandler
        self.progress_handler = progress_handler
        self.conv = conversation
        self.dir = dir
        if PRINT_LOG_FILES:
            print("FileReception: "
                  + ": responded to sender, ready to receive")

        self.status = "receiving"

    def on_data_received(self, conv, data):
        if not self.transmission_started:
            try:
                filesize, filename, metadata = _split_by_255(data)
                self.filesize = _from_b255_no_0s(filesize)
                self.filename = filename.decode('utf-8')
                self.metadata = metadata
                self.writer = open(os.path.join(
                    self.dir, self.filename + ".PART"), "wb")
                self.transmission_started = True
                self.conv.say("ready".encode())
                self.writtenbytes = 0
                if PRINT_LOG_FILES:
                    print("FileReception: " + self.filename
                          + ": ready to receive file")
                if self.progress_handler:
                    # run callback on a new thread, specifying only as many parameters as the callback wants
                    Thread(target=call_progress_callback,
                           args=(self.progress_handler,
                                 self.conv.peer_id,
                                 self.filename,
                                 self.filesize,
                                 0
                                 ),
                           name='FileTransmissionReceiver.progress'
                           ).start()

                if(self.filesize == 0):
                    self.finish()
            except:
                if PRINT_LOG_FILES:
                    print("Received unreadable data on FileTransmissionListener ")
                    traceback.print_exc()

        else:
            self.writer.write(data)
            self.writtenbytes += len(data)

            if self.progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(target=call_progress_callback,
                       args=(self.progress_handler,
                             self.conv.peer_id,
                             self.filename,
                             self.filesize,
                             self.writtenbytes / self.filesize
                             ),
                       name='FileTransmissionReceiver.progress'
                       ).start()

            if PRINT_LOG_FILES:
                print("FileTransmission: " + self.filename
                      + ": received data " + str(self.writtenbytes) + "/" + str(self.filesize))

            if self.writtenbytes == self.filesize:
                self.finish()
            elif self.writtenbytes > self.filesize:
                self.writer.close()
                raise UnreadableReply(
                    "Something weird happened, filesize is larger than expected.")

    def finish(self):
        self.writer.close()
        shutil.move(os.path.join(self.dir, self.filename + ".PART"),
                    os.path.join(self.dir, self.filename))
        if PRINT_LOG:
            print("FileReception: " + self.filename
                  + ": Transmission finished.")
        self.status = "finished"
        self.conv.close()
        if self.eventhandler:
            filepath = os.path.abspath(os.path.join(
                self.dir, self.filename))
            if signature(self.eventhandler).parameters["metadata"]:
                self.eventhandler(self.conv.peer_id, filepath, self.metadata)
            else:
                self.eventhandler(self.conv.peer_id, filepath)

    def terminate(self):
        self.conv.terminate()


def call_progress_callback(callback, peer_id, filename, filesize, progress):
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
        callback(peer_id, filename, filesize, progress)


class BufferSender():

    def __init__(self, peer_id, proto):
        self.peer_id = peer_id
        self.proto = proto
        self.sock = _create_sending_connection(peer_id, proto)

    def send_buffer(self, data):
        try:
            self.sock.send(data)
        except:
            self.sock = _create_sending_connection(self.peer_id, self.proto)
            self.sock.send(data)

    def terminate(self):
        _close_sending_connection(self.peer_id, self.proto)

    def __del__(self):
        self.terminate()


class BufferReceiver():
    def __init__(self,
                 eventhandler,
                 proto,
                 buffer_size=BUFFER_SIZE,
                 monitoring_interval=2,
                 status_eventhandler=None,
                 eventhandlers_on_new_threads=True):
        self.proto = proto
        self._listener = _ListenerTCP(
            eventhandler,
            0,
            buffer_size=buffer_size,
            monitoring_interval=monitoring_interval,
            status_eventhandler=status_eventhandler,
            eventhandlers_on_new_threads=eventhandlers_on_new_threads
        )
        _create_listening_connection(proto, self._listener.port)

    def terminate(self):
        _close_listening_connection(self.proto, self._listener.port)
        self._listener.terminate()

    def __del__(self):
        self.terminate()


def listen_to_buffers(eventhandler,
                      proto,
                      buffer_size=BUFFER_SIZE,
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


class _ListenerTCP(threading.Thread):
    """
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.
    Args:
        function(bytearray data, string sender_peer_idess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = BUFFER_SIZE
    _terminate = False
    sock = None
    last_time_recv = datetime.utcnow()

    def __init__(self,
                 eventhandler,
                 port=0,
                 buffer_size=BUFFER_SIZE,
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
                target=self.status_monitor, args=(), name='ListenerTP.status_monitor')
            self.status_monitor_thread.start()

        self.start()

        if PRINT_LOG_CONNECTIONS:
            print("Created listener.")

    def run(self):
        self.sock.listen(1)
        conn, ip_addr = self.sock.accept()

        while True:
            data = conn.recv(self.buffer_size)
            self.last_time_recv = datetime.utcnow()
            if(self._terminate == True):
                if PRINT_LOG_CONNECTIONS:
                    print("listener terminated")
                break
            if not data:
                if PRINT_LOG_CONNECTIONS:
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
        if PRINT_LOG_CONNECTIONS:
            print("Closed listener.")

    def status_monitor(self):
        while(True):
            if self._terminate:
                break
            time.sleep(self.monitoring_interval)
            if(datetime.utcnow() - self.last_time_recv).total_seconds() > self.monitoring_interval:
                self.status_eventhandler(
                    (datetime.utcnow() - self.last_time_recv).total_seconds())

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    # thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def terminate(self):
        if PRINT_LOG_CONNECTIONS:
            print("terminating listener")
        self._terminate = True   # marking the terminate flag as true
        self.sock.close()

    def __del__(self):
        self.terminate()


def listen_to_buffers_on_port(eventhandler,
                              port=0,
                              buffer_size=BUFFER_SIZE,
                              monitoring_interval=2,
                              status_eventhandler=None):
    return BufferReceiver(
        eventhandler,
        port,
        buffer_size,
        monitoring_interval,
        status_eventhandler
    )


class DataTransmissionError(Exception):
    """Is called when a fatal failure occurs during data transmission."""

    def __init__(self, message: str = "Failed to transmit the requested data to the specified peer."):
        self.message = message

    def __str__(self):
        return self.message


class PeerNotFound(Exception):
    """Is called when a function can't proceed because the desired IPFS peer
    can't be found on the internet. Simply trying again sometimes solves this.
    """

    def __init__(self, message: str = "Could not find the specified peer on the IPFS network. Perhaps try again."):
        self.message = message

    def __str__(self):
        return self.message


class InvalidPeer(Exception):
    """Is called when an invalid IPFS peer ID is provided."""

    def __init__(self, message: str = "The specified IPFS peer ID is invalid."):
        self.message = message

    def __str__(self):
        return self.message


class CommunicationTimeout(Exception):
    """Is called when a timeout is reached while trying to communicate with a
    peer.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class ConvListenTimeout(Exception):
    """Is called when one of the `.listen*` functions of a `Conversation`
    object yields no results. 
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class UnreadableReply(Exception):
    """Is called when a corrupted response is received from a peer while
    communicating.
    """

    def __init__(self, message: str = "Received data that we couldn't read."):
        self.message = message

    def __str__(self):
        return self.message


class IPFS_Error(Exception):
    """A generic error that arises from IPFS itself or our interaction with it.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


##
##
##
##
##
# ----- Utilities ------------------------------------------------------------
##
##
##
##


def __add_integritybyte_to_buffer(buffer):
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
def _to_b255_no_0s(number):
    array = bytearray([])
    while(number > 0):
        # modulus + 1 in order to get a range of possible values from 1-256 instead of 0-255
        array.insert(0, int(number % 255 + 1))
        number -= number % 255
        number = number / 255
    return array


def _from_b255_no_0s(array):
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


def _split_by_255(bytes):
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


def _tcp_send_all(sock, data):
    length = len(data)
    sock.send(_to_b255_no_0s(length) + bytearray([0]))
    sock.send(data)


def _tcp_recv_all(sock, timeout=5):
    # make socket non blocking
    sock.setblocking(0)

    # total data partwise in an array
    total_data = bytearray()
    data = bytearray()
    length = 0
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
            data = sock.recv(BUFFER_SIZE)
            if data:
                if not length:
                    if data.index(0):
                        total_data += data[:data.index(0)]
                        length = _from_b255_no_0s(total_data)
                        total_data = data[data.index(0) + 1:]
                    else:
                        total_data += data
                else:
                    total_data += data

                if length:
                    if len(total_data) == length:
                        return total_data
                    if len(total_data) > length:
                        raise Exception("Received more data than expected!")
                    # change the beginning time for measurement
                    begin = time.time()
        except:
            pass
    print("Timeout reached")
    # print("RECEIVED", type(total_data), total_data)
    return total_data


def _tcp_recv_buffer_timeout(sock, buffer_size=BUFFER_SIZE, timeout=5):
    # make socket non blocking
    # sock.setblocking(0)
    sock.settimeout(timeout)
    # beginning time
    begin = time.time()
    while 1:
        # timeout is reached
        if time.time() - begin > timeout:
            raise TimeoutError()

        # recv something
        try:
            data = sock.recv(buffer_size)
            if data:
                return data
        except:
            pass


# ----------IPFS Utilities-------------------------------------------
connections_send = list()
connections_listen = list()


def _create_sending_connection(peer_id: str, protocol: str, port=None):
    # _close_sending_connection(
    #     peer_id=peer_id, name=protocol)
    if port:
        _close_sending_connection(port=port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if port == None:
        for prt in sending_ports:   # trying ports until we find a free one
            try:
                ipfs_api.create_tcp_sending_connection(protocol, prt, peer_id)
                sock.connect(("127.0.0.1", prt))
                return sock
            except Exception as e:   # ignore errors caused by port already in use
                if not "bind: address already in use" in str(e):
                    raise IPFS_Error(str(e))
        raise IPFS_Error("Failed to find free port for sending connection")
    else:
        try:
            ipfs_api.create_tcp_sending_connection(protocol, port, peer_id)
            sock.connect(("127.0.0.1", prt))
            return sock
        except Exception as e:
            raise IPFS_Error(str(e))


def _create_listening_connection(protocol, port, force=True):
    """
    Args:
        bool force: whether or not already existing conflicting connections should be closed.
    """
    try:
        ipfs_api.create_tcp_listening_connection(protocol, port)
        if PRINT_LOG_CONNECTIONS:
            print(f"listening fas \"{protocol}\" on {port}")
    except:
        if force:
            _close_listening_connection(name=protocol)
        try:
            time.sleep(0.1)
            ipfs_api.create_tcp_listening_connection(protocol, port)
            if PRINT_LOG_CONNECTIONS:
                print(f"listening as \"{protocol}\" on {port}")
        except:
            raise IPFS_Error(
                "Error registering listening connection to IPFS: /x/" + protocol + "/ip4/127.0.0.1/udp/" + str(port))

    connections_listen.append((protocol, port))
    return port


def _close_sending_connection(peer_id=None, name=None, port=None):
    try:
        ipfs_api.close_tcp_sending_connection(
            peer_id=peer_id, name=name, port=port)
    except Exception as e:
        raise IPFS_Error(str(e))


def _close_listening_connection(name=None, port=None):
    try:
        ipfs_api.close_tcp_listening_connection(
            name=name, port=port)
    except Exception as e:
        raise IPFS_Error(str(e))
