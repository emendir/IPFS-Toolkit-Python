import tempfile
import logging
from .conversation_basics import BaseConversation
from .utils import (
    _to_b255_no_0s,
    _from_b255_no_0s,
    _split_by_255,
)
import shutil
from threading import Thread
import traceback
import os

# import inspect
from inspect import signature
from .config import (
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC,
    BLOCK_SIZE,
)

from ipfs_tk_generics.base_client import BaseClient
from .errors import InvalidPeer, UnreadableReply
from ipfs_tk_transmission.conversation_basics import ConversationListener
from typing import Callable

logger = logging.getLogger("IPFS-TK-Conversations")


def transmit_file(
    ipfs_client: BaseClient,
    filepath,
    peer_id,
    others_req_listener,
    metadata=bytearray(),
    progress_handler=None,
    encryption_callbacks=None,
    block_size=BLOCK_SIZE,
    transm_send_timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
    transm_req_max_retries=TRANSM_REQ_MAX_RETRIES,
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
        ipfs_client,
        filepath,
        peer_id,
        others_req_listener,
        metadata=metadata,
        progress_handler=progress_handler,
        encryption_callbacks=encryption_callbacks,
        block_size=block_size,
        transm_send_timeout_sec=transm_send_timeout_sec,
        transm_req_max_retries=transm_req_max_retries,
    )


def listen_for_file_transmissions(
    ipfs_client: BaseClient,
    listener_name: str,
    eventhandler: Callable,
    progress_handler: Callable | None = None,
    download_dir: str | None = None,
    encryption_callbacks: None = None,
) -> ConversationListener:
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
        download_dir (str): the directory in which received files should be written
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

    if download_dir == None:
        download_dir = tempfile.mkdtemp()

    def request_handler(conv_name, peer_id):
        logger.debug("Receiving file transmission...")
        ft = FileTransmissionReceiver()
        logger.debug("Creating conversation...")
        conv = BaseConversation(ipfs_client)
        logger.debug("Configuring file transmission receiver...")
        ft.setup(
            ipfs_client,
            conv,
            eventhandler,
            progress_handler=progress_handler,
            download_dir=download_dir,
        )
        logger.debug("Joining coversation...")
        conv.join(
            ipfs_client.tunnels.generate_name(conv_name),
            peer_id,
            conv_name,
            ft.on_data_received,
            encryption_callbacks=encryption_callbacks,
        )
        logger.debug("Starting file reception.")

    return ConversationListener(ipfs_client, listener_name, request_handler)


class FileTransmitter:
    """Object for managing file transmission (sending only, not receiving)"""

    status = "not started"  # "transmitting" "finished" "aborted"

    def __init__(
        self,
        ipfs_client: BaseClient,
        filepath: str,
        peer_id: str,
        others_req_listener: str,
        metadata: bytes = bytearray(),
        progress_handler: Callable | None = None,
        encryption_callbacks: None = None,
        block_size: int = BLOCK_SIZE,
        transm_send_timeout_sec: int = TRANSM_SEND_TIMEOUT_SEC,
        transm_req_max_retries: int = TRANSM_REQ_MAX_RETRIES,
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
        if peer_id == ipfs_client.peer_id:
            raise InvalidPeer(
                message="You cannot use your own IPFS peer ID as the recipient."
            )
        self.ipfs_client = ipfs_client
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
        self.conversation = BaseConversation(self.ipfs_client)
        logger.debug("starting file transmission")
        self.conversation.start(
            self.conv_name,
            self.peer_id,
            self.others_req_listener,
            data_received_eventhandler=self._hear,
            encryption_callbacks=self.encryption_callbacks,
            transm_send_timeout_sec=self._transm_send_timeout_sec,
            transm_req_max_retries=self._transm_req_max_retries,
        )
        self.conversation.say(
            _to_b255_no_0s(self.filesize)
            + bytearray([255])
            + bytearray(self.filename.encode())
            + bytearray([255])
            + self.metadata
        )
        logger.debug(
            "FileTransmission: "
            + self.filename
            + ": Sent transmission request"
        )
        self._call_progress_callback(0)

    def _start_transmission(self):
        logger.debug(
            "FileTransmission: " + self.filename + ": starting transmmission"
        )
        self.status = "transmitting"
        position = 0
        with open(self.filepath, "rb") as reader:
            while position < self.filesize:
                blocksize = self.filesize - position
                if blocksize > self.block_size:
                    blocksize = self.block_size
                data = reader.read(blocksize)
                position += len(data)
                self._call_progress_callback(
                    position / self.filesize,
                )

                logger.debug(
                    "FileTransmission: "
                    + self.filename
                    + ": sending data "
                    + str(position)
                    + "/"
                    + str(self.filesize)
                )
                self.conversation.say(data)
        logger.debug(
            "FileTransmission: "
            + self.filename
            + ": finished file transmission"
        )
        self.status = "finished"
        self.conversation.close()

    def _call_progress_callback(self, progress):
        if self.progress_handler:
            # run callback on a new thread, specifying only as many parameters as the callback wants
            Thread(
                target=call_progress_callback,
                args=(
                    self.progress_handler,
                    self.peer_id,
                    self.filename,
                    self.filesize,
                    progress,
                ),
                name="BaseConversation.progress_handler",
            ).start()

    def _hear(self, conv, data):
        logger.debug(
            "FileTransmission: "
            + self.filename
            + ": received response from receiver"
        )
        info = _split_by_255(data)
        if info[0].decode("utf-8") == "ready":
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

    def setup(
        self,
        ipfs_client: BaseClient,
        conversation,
        eventhandler,
        progress_handler=None,
        download_dir: str | None = None,
    ):
        """Configure this object to make it work.
        Args:
            conversation (BaseConversation): the BaseConversation object with which to
                        communicate with the transmitter
            eventhandler (function): function to be called when a file is
                        received
                        Parameters: (peer_id:str, path:str, metadata:bytes)
            progress_handler (function): function to be called whenever a block
                        of data is received during file transmission.
                        progress is a value between 0 and 1
                        Parameters: (peer_id:str, filesize:int, progress:float)

        """
        logger.debug("FileReception: " + ": Preparing to receive file")
        self.ipfs_client = ipfs_client
        self.eventhandler = eventhandler
        self.progress_handler = progress_handler
        self.conv = conversation
        if download_dir == None:
            self.download_dir = tempfile.mkdtemp()
        else:
            self.download_dir = download_dir
        logger.debug(
            "FileReception: " + ": responded to sender, ready to receive"
        )

        self.status = "receiving"

    def on_data_received(self, conv, data):
        if not self.transmission_started:
            logger.debug("Received first data!")
            try:
                logger.debug(data)
                filesize, filename, metadata = _split_by_255(data)
                self.filesize = _from_b255_no_0s(filesize)
                logger.debug(filename)
                self.filename = filename.decode("utf-8")
                self.metadata = metadata
                self.writer = open(
                    os.path.join(self.download_dir, self.filename + ".PART"),
                    "wb",
                )
                self.transmission_started = True
                self.conv.say("ready".encode())
                self.writtenbytes = 0
                logger.debug(
                    "FileReception: "
                    + self.filename
                    + ": ready to receive file"
                )
                if self.progress_handler:
                    # run callback on a new thread, specifying only as many parameters as the callback wants
                    Thread(
                        target=call_progress_callback,
                        args=(
                            self.progress_handler,
                            self.conv.peer_id,
                            self.filename,
                            self.filesize,
                            0,
                        ),
                        name="FileTransmissionReceiver.progress",
                    ).start()

                if self.filesize == 0:
                    self.finish()
            except:
                logger.error(
                    "Received unreadable data on FileTransmissionListener "
                )
                traceback.print_exc()

        else:
            logger.debug("Received file data...")
            self.writer.write(data)
            self.writtenbytes += len(data)

            if self.progress_handler:
                # run callback on a new thread, specifying only as many parameters as the callback wants
                Thread(
                    target=call_progress_callback,
                    args=(
                        self.progress_handler,
                        self.conv.peer_id,
                        self.filename,
                        self.filesize,
                        self.writtenbytes / self.filesize,
                    ),
                    name="FileTransmissionReceiver.progress",
                ).start()

            logger.debug(
                "FileTransmission: "
                + self.filename
                + ": received data "
                + str(self.writtenbytes)
                + "/"
                + str(self.filesize)
            )

            if self.writtenbytes == self.filesize:
                self.finish()
            elif self.writtenbytes > self.filesize:
                self.writer.close()
                raise UnreadableReply(
                    "Something weird happened, filesize is larger than expected."
                )

    def finish(self):
        self.writer.close()
        shutil.move(
            os.path.join(self.download_dir, self.filename + ".PART"),
            os.path.join(self.download_dir, self.filename),
        )
        logger.debug(
            "FileReception: " + self.filename + ": Transmission finished."
        )
        self.status = "finished"
        self.conv.close()
        if self.eventhandler:
            filepath = os.path.abspath(
                os.path.join(self.download_dir, self.filename)
            )
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
