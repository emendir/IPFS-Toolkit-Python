from queue import Queue, Empty as QueueEmpty
from threading import Thread, Event
from datetime import datetime, UTC
import time
# import inspect
from inspect import signature
try:
    import ipfs_api
except:
    import IPFS_API_Remote_Client as ipfs_api


from .config import (
    PRINT_LOG,
    PRINT_LOG_CONVERSATIONS,
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC,
    BLOCK_SIZE,
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
        self.file_listener = None
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
        if (PRINT_LOG_CONVERSATIONS):
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
        self._last_coms_time = datetime.now(UTC)
        if PRINT_LOG_CONVERSATIONS:
            print(conv_name + ": sent conversation request")
        success = self.started.wait(transm_send_timeout_sec)
        if not success:
            raise CommunicationTimeout(
                f"Successfully transmitted conversation request but received no reply within timeout of {transm_send_timeout_sec}s.")
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
                        f"{self.conv_name}: other's proto is {self.others_trsm_listener}")
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
                raise ConvListenTimeout("Didn't receive any data.") from None

        if data:
            return data
        else:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.listen: received nothing restarting Event Wait")
            self.listen()

    def _file_received(self, peer, filepath, metadata):
        """Receives this conversation's file transmissions."""
        self._last_coms_time = datetime.now(UTC)

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
        start_time = datetime.now(UTC)
        if not (abs_timeout or no_coms_timeout):    # if no timeouts are specified
            data = self._file_queue.get()
        else:   # timeouts are specified
            while True:
                # calculate timeouts relative to current time
                if no_coms_timeout:
                    # time left till next coms timeout check
                    _no_coms_timeout = no_coms_timeout - \
                        (datetime.now(UTC) - self._last_coms_time).total_seconds()
                if abs_timeout:
                    # time left till absolute timeout would be reached
                    _abs_timeout = abs_timeout - \
                        (datetime.now(UTC) - start_time).total_seconds()

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
                    if abs_timeout and (datetime.now(UTC) - start_time).total_seconds() > abs_timeout:
                        raise ConvListenTimeout(
                            "Didn't receive any files.") from None
                    elif (datetime.now(UTC) - self._last_coms_time).total_seconds() > no_coms_timeout:
                        raise CommunicationTimeout(
                            "Communication timeout reached while waiting for file.") from None
        if data:
            return data
        else:
            if PRINT_LOG_CONVERSATIONS:
                print("Conv.FileListen: received nothign restarting Event Wait")
            self.listen_for_file(timeout)

    def _on_file_progress_received(self, peer_id: str, filename: str, filesize: str, progress):
        self._last_coms_time = datetime.now(UTC)
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
        self._last_coms_time = datetime.now(UTC)
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
            self._last_coms_time = datetime.now(UTC)
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
        if self._terminate:
            return
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
        if (PRINT_LOG_CONVERSATIONS):
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
        if PRINT_LOG_CONVERSATIONS:
            print(f"Conv.terminate: closing liseter for {self._listener_name}")
        self._listener.terminate()

    def __del__(self):
        self.terminate()
