""" """

import tempfile

import inspect

from typing import Callable
from ipfs_tk_generics.base_client import BaseClient
from .errors import (
    InvalidPeer,
    CommunicationTimeout,
    ConvListenTimeout,
)
from .transmission import (
    transmit_data,
    listen_for_transmissions,
)
from .utils import _split_by_255, disprepend_bytearray_segment
from queue import Queue
from threading import Thread, Event
from datetime import datetime, timezone
import time

# import inspect
from inspect import signature

import logging
from .config import (
    PRINT_LOG,
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC,
)

logger = logging.getLogger("IPFS-TK-Conversations")

UTC = timezone.utc


class BaseConversation:
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

        self.salutation_start = bytearray([])
        self.salutation_join = bytearray([])

    def start(
        self,
        conv_name: str,
        peer_id: str,
        others_req_listener: str,
        data_received_eventhandler: Callable | None = None,
        encryption_callbacks: None = None,
        transm_send_timeout_sec: int = _transm_send_timeout_sec,
        transm_req_max_retries: int = _transm_req_max_retries,
        download_dir: str | None = None,
        salutation_message: bytes | None = None,
    ):
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
            download_dir (str): the path where received files should be downloaded to
        """
        if peer_id == self.ipfs_client.peer_id:
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as your conversation partner."
            )
        logger.debug(conv_name + ": Starting conversation")
        self.conv_name = conv_name
        if download_dir == None:
            self.download_dir = tempfile.mkdtemp()
        else:
            self.download_dir = download_dir
        self.data_received_eventhandler = data_received_eventhandler
        if encryption_callbacks:
            self._encryption_callback = encryption_callbacks[0]
            self._decryption_callback = encryption_callbacks[1]
        self._transm_send_timeout_sec = transm_send_timeout_sec
        self._transm_req_max_retries = transm_req_max_retries

        self.peer_id = peer_id
        logger.debug(
            conv_name
            + f": sending conversation request, {others_req_listener}"
        )
        self._listener = listen_for_transmissions(
            self.ipfs_client, conv_name, self._hear
        )
        self.salutation_start = salutation_message
        # self._listener = listen_for_transmissions(conv_name, self.hear_eventhandler)

        # BACKWARD COMPATIBILITY
        use_unversioned_protocol = not salutation_message
        if use_unversioned_protocol:
            data = (
                bytearray("I want to start a conversation".encode("utf-8"))
                + bytearray([255])
                + bytearray(conv_name.encode("utf-8"))
            )
        else:
            data = (
                bytearray([255])
                # bytearray([0]) is a format specifier, providing room for
                # future extensions
                + bytearray([0])
                + bytearray([255])
                + bytearray("I want to start a conversation".encode("utf-8"))
                + bytearray([255])
                + bytearray(conv_name.encode("utf-8"))
                + bytearray([255])
            )
            if salutation_message:
                data += bytearray(salutation_message)
        try:
            transmit_data(
                self.ipfs_client,
                data,
                peer_id,
                others_req_listener,
                self._transm_send_timeout_sec,
                self._transm_req_max_retries,
            )
        except Exception as e:
            self.terminate()
            raise e
        self._last_coms_time = datetime.now(UTC)
        logger.debug(
            f"{conv_name}: sent conversation request to {others_req_listener}"
        )
        success = self.started.wait(transm_send_timeout_sec)
        if not success:
            print(
                f"{conv_name}: IPFS tunnels: "
                f"{self.ipfs_client.tunnels.get_tunnels().listeners}"
            )
            raise CommunicationTimeout(
                "Successfully transmitted conversation request but received no"
                f" reply within timeout of {transm_send_timeout_sec}s."
            )

        return True  # signal success

    def join(
        self,
        conv_name,
        peer_id,
        others_trsm_listener,
        data_received_eventhandler=None,
        encryption_callbacks=None,
        transm_send_timeout_sec=_transm_send_timeout_sec,
        transm_req_max_retries=_transm_req_max_retries,
        download_dir: str | None = None,
        salutation_message: bytes | None = None,
    ):
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
            download_dir (str): the path where received files should be downloaded to
        """
        self.conv_name = conv_name
        if download_dir == None:
            self.download_dir = tempfile.mkdtemp()
        else:
            self.download_dir = download_dir
        self.download_dir = download_dir
        logger.debug(
            conv_name + ": Joining conversation " + others_trsm_listener
        )
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
        self.salutation_join = salutation_message

        # BACKWARD COMPATIBILITY
        use_unversioned_protocol = not salutation_message
        if use_unversioned_protocol:
            data = (
                bytearray("I'm listening".encode("utf-8"))
                + bytearray([255])
                + bytearray(conv_name.encode("utf-8"))
            )
        else:
            # new, version-controlled format
            data = (
                bytearray([255])
                # bytearray([0]) is a format specifier, providing room for
                # future extensions
                + bytearray([0])
                + bytearray([255])
                + bytearray("I'm listening".encode("utf-8"))
                + bytearray([255])
                + bytearray(conv_name.encode("utf-8"))
                + bytearray([255])
            )
            if salutation_message:
                data += bytearray(salutation_message)
        self._conversation_started = True
        logger.debug(
            f"{conv_name}: Sending join-response to {others_trsm_listener}"
        )
        # logger.debug(f"Tunnels: {self.ipfs_client.tunnels.get_tunnels()}")
        import time

        time.sleep(0.5)  # TODO: FIX THIS DELAY WITH TRNAMISSION RETRIES
        transmit_data(self.ipfs_client, data, peer_id, others_trsm_listener)
        self._last_coms_time = datetime.now(UTC)
        logger.debug(
            conv_name + ": Joined conversation " + others_trsm_listener
        )
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
            if data[0] == 255:
                data = data[1:]
                separator_count = data.count(255)
                if separator_count < 1:
                    raise Exception("Received unreadable request")
                version, data = disprepend_bytearray_segment(data, 255)
                separator_count -= 1

                match tuple(version):
                    case (0,):
                        if separator_count < 1:
                            raise Exception(
                                f"ConvLisReceived {self.conv_name}: "
                                f"Received unreadable request in protocol version: "
                                f"{version}"
                            )
                        prelude, data = disprepend_bytearray_segment(data, 255)
                        separator_count -= 1
                        if prelude != bytearray(
                            "I'm listening".encode("utf-8")
                        ):
                            raise Exception(
                                f"ConvLisReceived {self.conv_name}: "
                                f"Received unreadable request in protocol version: "
                                f"{version}"
                            )
                        if separator_count < 1:
                            raise Exception(
                                f"ConvLisReceived {self.conv_name}: "
                                f"Received unreadable request in protocol version: "
                                f"{version}"
                            )
                        _conv_name, data = disprepend_bytearray_segment(
                            data, 255
                        )
                        self.others_trsm_listener = _conv_name.decode()
                        separator_count -= 1
                        self.salutation_join = data
            else:
                info = _split_by_255(data)
                if bytearray(info[0]) == bytearray(
                    "I'm listening".encode("utf-8")
                ):
                    self.others_trsm_listener = info[1].decode("utf-8")

                else:
                    raise Exception(
                        f"{self.conv_name}"
                        ": received unrecognisable buffer, expected join confirmation"
                        f"{info}"
                    )

            logger.debug(
                f"{self.conv_name}: other's proto is "
                f"{self.others_trsm_listener}"
            )
            # self.hear_eventhandler = self._hear
            self._conversation_started = True
            logger.debug(
                self.conv_name + ": peer joined, conversation started"
            )
            self.started.set()
            return
        else:  # conversation has already started
            if self._decryption_callback:
                logger.debug("Conv._hear: decrypting message")
                data = self._decryption_callback(data)
            self.message_queue.put(data)
            logger.debug(
                f"Conv._hear: received and queued message of length "
                f"{len(data)} bytes"
            )

            if self.data_received_eventhandler:
                # if the data_received_eventhandler has 2 parameters
                if (
                    len(signature(self.data_received_eventhandler).parameters)
                    == 2
                ):
                    Thread(
                        target=self.data_received_eventhandler,
                        args=(self, data),
                        name="Converstion.data_received_eventhandler",
                    ).start()
                else:
                    Thread(
                        target=self.data_received_eventhandler,
                        args=(self, data, arg3),
                        name="Converstion.data_received_eventhandler",
                    ).start()

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
            except Exception as e:  # timeout reached
                logger.error(e)
                raise ConvListenTimeout("Didn't receive any data.") from None

        if data:
            return data
        else:
            logger.debug("Conv.listen: received nothing restarting Event Wait")
            self.listen()

    def say(
        self,
        data,
        timeout_sec=_transm_send_timeout_sec,
        max_retries=_transm_req_max_retries,
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
            logger.debug(
                "Wanted to say something but conversation was not yet started"
            )
            time.sleep(0.01)
        if self._encryption_callback:
            logger.debug("Conv.say: encrypting message")
            data = self._encryption_callback(data)
        transmit_data(
            self.ipfs_client,
            data,
            self.peer_id,
            self.others_trsm_listener,
            timeout_sec,
            max_retries,
        )
        self._last_coms_time = datetime.now(UTC)
        return True

    def terminate(self):
        """Stop the conversation and clean up IPFS connection configurations."""
        if self._terminate:
            return
        self._terminate = True
        if self._listener:
            self._listener.terminate()

    def close(self):
        """Stop the conversation and clean up IPFS connection configurations."""
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

    def __init__(
        self,
        ipfs_client: BaseClient,
        listener_name: str,
        eventhandler: Callable,
    ):
        self.ipfs_client = ipfs_client
        self._listener_name = listener_name
        logger.debug("Listening for conversations as " + listener_name)
        self.eventhandler = eventhandler
        self._listener = listen_for_transmissions(
            self.ipfs_client, listener_name, self._on_request_received
        )

    def _on_request_received(self, data, peer_id):
        logger.debug(
            f"ConvLisReceived {self._listener_name}: "
            "Received Conversation Request"
        )
        if data[0] == 255:
            data = data[1:]
            separator_count = data.count(255)
            if separator_count < 1:
                raise Exception("Received unreadable request")
            version, data = disprepend_bytearray_segment(data, 255)
            separator_count -= 1

            match tuple(version):
                case (0,):
                    if separator_count < 1:
                        raise Exception(
                            f"ConvLisReceived {self._listener_name}: "
                            f"Received unreadable request in protocol version: "
                            f"{version}"
                        )
                    prelude, data = disprepend_bytearray_segment(data, 255)
                    separator_count -= 1
                    if prelude != bytearray(
                        "I want to start a conversation".encode("utf-8")
                    ):
                        raise Exception(
                            f"ConvLisReceived {self._listener_name}: "
                            f"Received unreadable request in protocol version: "
                            f"{version}"
                        )
                    if separator_count < 1:
                        raise Exception(
                            f"ConvLisReceived {self._listener_name}: "
                            f"Received unreadable request in protocol version: "
                            f"{version}"
                        )
                    _conv_name, data = disprepend_bytearray_segment(data, 255)
                    conv_name = _conv_name.decode()
                    separator_count -= 1
                    self.salutation_start = data
                    sig = inspect.signature(self.eventhandler)
                    params = sig.parameters
                    num_params = len(params)
                    if num_params == 2:
                        self.eventhandler(conv_name, peer_id)
                    elif num_params > 2:
                        self.eventhandler(
                            conv_name, peer_id, self.salutation_start
                        )
                    else:
                        raise Exception(
                            f"ConvLisReceived {self._listener_name}: "
                            f"eventhandler only has {num_params} parameters"
                        )
                case _:
                    raise Exception(
                        f"ConvLisReceived {self._listener_name}: "
                        f"Received unreadable protocol version: {version}"
                    )

        else:  # old protocol before versioning was introduced
            info = _split_by_255(data)
            if info[0] == bytearray(
                "I want to start a conversation".encode("utf-8")
            ):
                logger.debug(
                    f"ConvLisReceived {self._listener_name}: "
                    "Starting conversation..."
                )
                conv_name = info[1].decode("utf-8")
                self.eventhandler(conv_name, peer_id)
            else:
                raise Exception(
                    f"ConvLisReceived {self._listener_name}: "
                    "Received unreadable request:"
                    f"{data}"
                )

    def terminate(self):
        """Stop listening for conversation requests and clean up IPFS
        connection configurations.
        """
        logger.debug(
            f"Conv.terminate: closing liseter for {self._listener_name}"
        )
        self._listener.terminate()

    def __del__(self):
        self.terminate()
