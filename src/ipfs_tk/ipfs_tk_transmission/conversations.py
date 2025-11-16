""" """

from typing import Callable
from .file_transmission import (
    listen_for_file_transmissions,
    transmit_file,
    call_progress_callback,
)
from .conversation_basics import (
    BaseConversation,
    ConversationListener,
)
from ipfs_tk_generics.base_client import BaseClient
from .errors import (
    CommunicationTimeout,
    ConvListenTimeout,
)
from .config import (
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC,
    BLOCK_SIZE,
)
from queue import Queue, Empty as QueueEmpty

from threading import Thread
from datetime import datetime, timezone
import time

# import inspect
import logging

logger = logging.getLogger("IPFS-TK-Conversations")


UTC = timezone.utc


def start_conversation(
    ipfs_client: BaseClient,
    conv_name: str,
    peer_id: str,
    others_req_listener: str,
    data_received_eventhandler: Callable | None = None,
    file_eventhandler: None = None,
    file_progress_callback: None = None,
    encryption_callbacks: None = None,
    timeout_sec: int = TRANSM_SEND_TIMEOUT_SEC,
    max_retries: int = TRANSM_REQ_MAX_RETRIES,
    download_dir: str | None = None,
    salutation_message: bytearray | None = None,
):
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
        download_dir (str): the path where received files should be downloaded to
    Returns:
        Conversation: an object through which messages and files can be sent
    """
    conv = Conversation(ipfs_client)
    conv.start(
        conv_name,
        peer_id,
        others_req_listener,
        data_received_eventhandler,
        file_eventhandler=file_eventhandler,
        file_progress_callback=file_progress_callback,
        encryption_callbacks=encryption_callbacks,
        transm_send_timeout_sec=timeout_sec,
        transm_req_max_retries=max_retries,
        download_dir=download_dir,
        salutation_message=salutation_message,
    )
    return conv


def join_conversation(
    ipfs_client: BaseClient,
    conv_name,
    peer_id,
    others_trsm_listener,
    data_received_eventhandler=None,
    file_eventhandler=None,
    file_progress_callback=None,
    encryption_callbacks=None,
    timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
    max_retries=TRANSM_REQ_MAX_RETRIES,
    download_dir=None,
    salutation_message: bytearray | None = None,
):
    """Join a conversation object started by another peer.
    Call `.terminate()` on the returned Conversation object when you
    no longer need it to clean up IPFS connection configurations.
    Args:
        conv_name (str): the name of the IPFS port forwarding connection
                                (IPFS Libp2pStreamMounting protocol)
        peer_id (str): the IPFS peer ID of the node to communicate with
        others_trsm_listener (str): the name of the ther peer's conversation
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
        download_dir (str): the path where received files should be downloaded to
    Returns:
        Conversation: an object through which messages and files can be sent
    """
    conv = Conversation(ipfs_client)
    conv.join(
        conv_name,
        peer_id,
        others_trsm_listener,
        data_received_eventhandler,
        file_eventhandler=file_eventhandler,
        file_progress_callback=file_progress_callback,
        encryption_callbacks=encryption_callbacks,
        transm_send_timeout_sec=timeout_sec,
        transm_req_max_retries=max_retries,
        download_dir=download_dir,
        salutation_message=salutation_message,
    )
    return conv


def listen_for_conversations(
    ipfs_client: BaseClient, listener_name: str, eventhandler
):
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
    return ConversationListener(ipfs_client, listener_name, eventhandler)


class Conversation(BaseConversation):
    """Communication object which allows 2 peers to repetatively make
    data transmissions to each other asynchronously and bidirectionally.
    """

    file_progress_callback = None

    def __init__(self, ipfs_client: BaseClient):
        BaseConversation.__init__(self, ipfs_client)
        self.file_listener = None
        self.file_eventhandler = None
        self.file_progress_callback = None
        self._file_queue: Queue[dict] = Queue()

    def start(
        self,
        conv_name: str,
        peer_id: str,
        others_req_listener: str,
        data_received_eventhandler: Callable | None = None,
        file_eventhandler: None = None,
        file_progress_callback: None = None,
        encryption_callbacks: None = None,
        transm_send_timeout_sec: int = BaseConversation._transm_send_timeout_sec,
        transm_req_max_retries: int = BaseConversation._transm_req_max_retries,
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
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback
        result = BaseConversation.start(
            self,
            conv_name=conv_name,
            peer_id=peer_id,
            others_req_listener=others_req_listener,
            data_received_eventhandler=data_received_eventhandler,
            encryption_callbacks=encryption_callbacks,
            transm_send_timeout_sec=transm_send_timeout_sec,
            transm_req_max_retries=transm_req_max_retries,
            download_dir=download_dir,
            salutation_message=salutation_message,
        )
        self.setup_file_listener()
        return result

    def join(
        self,
        conv_name,
        peer_id,
        others_trsm_listener,
        data_received_eventhandler=None,
        file_eventhandler=None,
        file_progress_callback=None,
        encryption_callbacks=None,
        transm_send_timeout_sec=BaseConversation._transm_send_timeout_sec,
        transm_req_max_retries=BaseConversation._transm_req_max_retries,
        download_dir=None,
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
        self.file_eventhandler = file_eventhandler
        self.file_progress_callback = file_progress_callback

        result = BaseConversation.join(
            self,
            conv_name=conv_name,
            peer_id=peer_id,
            others_trsm_listener=others_trsm_listener,
            data_received_eventhandler=data_received_eventhandler,
            encryption_callbacks=encryption_callbacks,
            transm_send_timeout_sec=transm_send_timeout_sec,
            transm_req_max_retries=transm_req_max_retries,
            download_dir=download_dir,
            salutation_message=salutation_message,
        )
        self.setup_file_listener()
        return result

    def setup_file_listener(self):
        if self.file_listener:
            self.file_listener.terminate()
        self.file_listener = listen_for_file_transmissions(
            self.ipfs_client,
            f"{self.conv_name}:files",
            self._file_received,
            progress_handler=self._on_file_progress_received,
            download_dir=self.download_dir,
            encryption_callbacks=(
                self._encryption_callback,
                self._decryption_callback,
            ),
        )

    def set_encryption_functions(self, encrypt: Callable, decrypt: Callable):
        self._encryption_callback = encrypt
        self._decryption_callback = decrypt
        self.setup_file_listener()

    def _file_received(self, peer, filepath, metadata):
        """Receives this conversation's file transmissions."""
        self._last_coms_time = datetime.now(UTC)

        logger.debug(f"{self.conv_name}: Received file: {filepath}")
        self._file_queue.put({"filepath": filepath, "metadata": metadata})
        if self.file_eventhandler:
            Thread(
                target=self.file_eventhandler,
                args=(self, filepath, metadata),
                name="Conversation.file_eventhandler",
            ).start()

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
        start_time = datetime.now(UTC)
        if not (
            abs_timeout or no_coms_timeout
        ):  # if no timeouts are specified
            data = self._file_queue.get()
        else:  # timeouts are specified
            while True:
                # calculate timeouts relative to current time
                if no_coms_timeout:
                    # time left till next coms timeout check
                    _no_coms_timeout = (
                        no_coms_timeout
                        - (
                            datetime.now(UTC) - self._last_coms_time
                        ).total_seconds()
                    )
                if abs_timeout:
                    # time left till absolute timeout would be reached
                    _abs_timeout = (
                        abs_timeout
                        - (datetime.now(UTC) - start_time).total_seconds()
                    )

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
                    if (
                        abs_timeout
                        and (datetime.now(UTC) - start_time).total_seconds()
                        > abs_timeout
                    ):
                        raise ConvListenTimeout(
                            "Didn't receive any files."
                        ) from None
                    elif (
                        datetime.now(UTC) - self._last_coms_time
                    ).total_seconds() > no_coms_timeout:
                        raise CommunicationTimeout(
                            "Communication timeout reached while waiting for file."
                        ) from None
        if data:
            return data
        else:
            logger.debug(
                "Conv.FileListen: received nothign restarting Event Wait"
            )
            return self.listen_for_file(timeout)

    def _on_file_progress_received(
        self, peer_id: str, filename: str, filesize: str, progress
    ):
        self._last_coms_time = datetime.now(UTC)
        if self.file_progress_callback:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(
                target=call_progress_callback,
                args=(
                    self.file_progress_callback,
                    peer_id,
                    filename,
                    filesize,
                    progress,
                ),
                name="Conversation.progress_handler",
            ).start()

            # if len(signature(self.progress_handler).parameters) == 1:
            #     self.file_progress_callback(progress)
            # elif len(signature(self.progress_handler).parameters) == 2:
            #     self.file_progress_callback(filename, progress)
            # elif len(signature(self.progress_handler).parameters) == 3:
            #     self.file_progress_callback(
            #         filename, filesize, progress)

    def transmit_file(
        self,
        filepath,
        metadata=bytearray(),
        progress_handler=file_progress_callback,
        block_size=BLOCK_SIZE,
        transm_send_timeout_sec=BaseConversation._transm_send_timeout_sec,
        transm_req_max_retries=BaseConversation._transm_req_max_retries,
    ):
        """
        Transmits the provided file to the other computer in this conversation.

        """
        while not self._conversation_started:
            logger.debug(
                "Wanted to say something but conversation was not yet started"
            )
            time.sleep(0.01)
        logger.debug(f"Transmitting file to {self.others_trsm_listener}:files")

        def _progress_handler(
            peer_id: str, filename: str, filesize: str, progress
        ):
            self._last_coms_time = datetime.now(UTC)
            if progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(
                    target=call_progress_callback,
                    args=(
                        progress_handler,
                        peer_id,
                        filename,
                        filesize,
                        progress,
                    ),
                    name="Conversation.progress_handler",
                ).start()

        return transmit_file(
            self.ipfs_client,
            filepath,
            self.peer_id,
            f"{self.others_trsm_listener}:files",
            metadata,
            _progress_handler,
            encryption_callbacks=(
                self._encryption_callback,
                self._decryption_callback,
            ),
            block_size=block_size,
            transm_send_timeout_sec=transm_send_timeout_sec,
            transm_req_max_retries=transm_req_max_retries,
        )

    def terminate(self):
        """Stop the conversation and clean up IPFS connection configurations."""
        BaseConversation.terminate(self)
        if self.file_listener:
            self.file_listener.terminate()

    def close(self):
        """Stop the conversation and clean up IPFS connection configurations."""
        self.terminate()

    def __del__(self):
        self.terminate()
