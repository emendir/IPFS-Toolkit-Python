"""
"""
from .utils import (
    _split_by_255,
)
from queue import Queue
from threading import Thread, Event
from datetime import datetime, UTC
import time
# import inspect
from inspect import signature


from .config import (
    PRINT_LOG,
    PRINT_LOG_CONVERSATIONS,
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC
)
from .transmission import (
    transmit_data,
    listen_for_transmissions,
)

from .errors import (
    InvalidPeer,
    CommunicationTimeout,
    ConvListenTimeout,
)
from ipfs_tk_generics.base_client import BaseClient
from typing import Callable


class BaseConversation():
    """Communication object which allows 2 peers to repetatively make
    data transmissions to each other asynchronously and bidirectionally.
    """
    conv_name = ""
    peer_id = ""
    data_received_eventhandler = None
    _transm_send_timeout_sec = TRANSM_SEND_TIMEOUT_SEC
    _transm_req_max_retries = TRANSM_REQ_MAX_RETRIES
    _listener = None


    _last_coms_time: datetime | None = None

    def __init__(self, ipfs_client: BaseClient):
        self.ipfs_client = ipfs_client
        self.started = Event()
        self._conversation_started = False
        self.data_received_eventhandler = None
        self.message_queue: Queue[bytes] = Queue()
        
        self._encryption_callback = None
        self._decryption_callback = None
        self._terminate = False

    def start(self,
              conv_name: str,
              peer_id: str,
              others_req_listener: str,
              data_received_eventhandler: Callable | None = None,
              encryption_callbacks: None = None,
              transm_send_timeout_sec: int = _transm_send_timeout_sec,
              transm_req_max_retries: int = _transm_req_max_retries,
              dir: str = "."):
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
        if peer_id == self.ipfs_client.peer_id:
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as your conversation partner.")
        if (PRINT_LOG_CONVERSATIONS):
            print(conv_name + ": Starting conversation")
        self.conv_name = conv_name
        self.data_received_eventhandler = data_received_eventhandler
        if encryption_callbacks:
            self._encryption_callback = encryption_callbacks[0]
            self._decryption_callback = encryption_callbacks[1]
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries

        self.peer_id = peer_id
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": sending conversation request")
        self._listener = listen_for_transmissions(
            self.ipfs_client, conv_name,self._hear
        )
        # self._listener = listen_for_transmissions(conv_name, self.hear_eventhandler)
        data = bytearray("I want to start a conversation".encode(
            'utf-8')) + bytearray([255]) + bytearray(conv_name.encode('utf-8'))
        try:
            transmit_data(self.ipfs_client,
                          data,
                          peer_id,
                          others_req_listener,
                          self._transm_send_timeout_sec,
                          self._transm_req_max_retries
                          )
        except Exception as e:
            self.terminate()
            raise e
        self._last_coms_time = datetime.now(UTC)
        if PRINT_LOG_CONVERSATIONS:
            print(
                f"{conv_name}: sent conversation request to "
                f"{others_req_listener}"
            )
        success = self.started.wait(transm_send_timeout_sec)
        if not success:
            print(f"{conv_name}: IPFS tunnels: "
                f"{self.ipfs_client.tunnels.get_tunnels().listeners}")
            raise CommunicationTimeout(
                "Successfully transmitted conversation request but received no"
                f" reply within timeout of {transm_send_timeout_sec}s.")

        return True     # signal success

    def join(self,
             conv_name,
             peer_id,
             others_trsm_listener,
             data_received_eventhandler=None,
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
        if encryption_callbacks:
            self._encryption_callback = encryption_callbacks[0]
            self._decryption_callback = encryption_callbacks[1]
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries
        self._listener = listen_for_transmissions(
            self.ipfs_client,
            conv_name,
            self._hear,
        )

        self.others_trsm_listener = others_trsm_listener
        self.peer_id = peer_id
        data = bytearray("I'm listening".encode(
            'utf-8')) + bytearray([255]) + bytearray(conv_name.encode('utf-8'))
        self._conversation_started = True
        if PRINT_LOG_CONVERSATIONS:
            print(f"{conv_name}: Sending join-response to "
                f"{others_trsm_listener}")
            print("Tunnels:", self.ipfs_client.tunnels.get_tunnels())
        import time;time.sleep(0.5)#TODO: FIX THIS DELAY WITH TRNAMISSION RETRIES
        transmit_data(self.ipfs_client, data, peer_id, others_trsm_listener)
        self._last_coms_time = datetime.now(UTC)
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
        self._last_coms_time = datetime.now(UTC)

        if not self._conversation_started:
            info = _split_by_255(data)
            if bytearray(info[0]) == bytearray("I'm listening".encode('utf-8')):
                self.others_trsm_listener = info[1].decode('utf-8')
                if PRINT_LOG_CONVERSATIONS:
                    print(
                        f"{self.conv_name}: other's proto is "
                        f"{self.others_trsm_listener}"
                    )
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
            if self._decryption_callback:
                if PRINT_LOG_CONVERSATIONS:
                    print("Conv._hear: decrypting message")
                data = self._decryption_callback(data)
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
                raise ConvListenTimeout("Didn't receive any data.") from None

        if data:
            return data
        else:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.listen: received nothing restarting Event Wait")
            self.listen()

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
        if self._encryption_callback:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.say: encrypting message")
            data = self._encryption_callback(data)
        transmit_data(self.ipfs_client,data, self.peer_id, self.others_trsm_listener,
                      timeout_sec, max_retries)
        self._last_coms_time = datetime.now(UTC)
        return True

    def terminate(self):
        """Stop the conversation and clean up IPFS connection configurations.
        """
        if self._terminate:
            return
        self._terminate = True
        if self._listener:
            self._listener.terminate()

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

    def __init__(self, ipfs_client: BaseClient, listener_name: str, eventhandler: Callable):
        self.ipfs_client = ipfs_client
        self._listener_name = listener_name
        if (PRINT_LOG_CONVERSATIONS):
            print("Listening for conversations as " + listener_name)
        self.eventhandler = eventhandler
        self._listener = listen_for_transmissions(
            self.ipfs_client,
            listener_name, self._on_request_received
        )

    def _on_request_received(self, data, peer_id):
        if PRINT_LOG_CONVERSATIONS:
            print(
                f"ConvLisReceived {self._listener_name}: "
                "Received Conversation Request"
            )
        info = _split_by_255(data)
        if info[0] == bytearray("I want to start a conversation".encode('utf-8')):
            if PRINT_LOG_CONVERSATIONS:
                print(
                    f"ConvLisReceived {self._listener_name}: "
                    "Starting conversation..."
                )
            conv_name = info[1].decode('utf-8')
            self.eventhandler(conv_name, peer_id)
        elif PRINT_LOG_CONVERSATIONS:
            print(
                f"ConvLisReceived {self._listener_name}: "
                "Received unreadable request"
            )
            print(info[0])

    def terminate(self):
        """Stop listening for conversation requests and clean up IPFS
        connection configurations.
        """
        if PRINT_LOG_CONVERSATIONS:
            print(f"Conv.terminate: closing liseter for {self._listener_name}")
        self._listener.terminate()

    def __del__(self):
        self.terminate()
