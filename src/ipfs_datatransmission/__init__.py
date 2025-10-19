from ipfs_api import client as ipfs_client

from ipfs_tk_transmission.config import (
    TRANSM_SEND_TIMEOUT_SEC,
    TRANSM_REQ_MAX_RETRIES,
    BLOCK_SIZE
)
from ipfs_tk_transmission.errors import (
    DataTransmissionError,
    PeerNotFound,
    InvalidPeer,
    CommunicationTimeout,
    ConvListenTimeout,
    UnreadableReply,
    IPFS_Error,
)

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
    return ipfs_client.transmit_data(
                         data=data,
                         peer_id=peer_id,
                         req_lis_name=req_lis_name,
                         timeout_sec=timeout_sec,
                         max_retries=max_retries,
                         )


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
    return ipfs_client.listen_for_transmissions(listener_name, eventhandler)


def transmit_file(
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
    return ipfs_client.transmit_file(
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


def listen_for_file_transmissions(
                                  listener_name,
                                  eventhandler,
                                  progress_handler=None,
                                  download_dir:str|None=None,
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
    return ipfs_client.listen_for_file_transmissions(
        listener_name=listener_name,
        eventhandler=eventhandler,
        progress_handler=progress_handler,
        download_dir=download_dir,
        encryption_callbacks=encryption_callbacks,
    )


def start_conversation(
        conv_name,
        peer_id,
        others_req_listener,
        data_received_eventhandler=None,
        file_eventhandler=None,
        file_progress_callback=None,
        encryption_callbacks=None,
        timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
        max_retries=TRANSM_REQ_MAX_RETRIES,
        download_dir:str|None=None):
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
    return ipfs_client.start_conversation(
        conv_name=conv_name,
        peer_id=peer_id,
        others_req_listener=others_req_listener,
        data_received_eventhandler=data_received_eventhandler,
        file_eventhandler=file_eventhandler,
        file_progress_callback=file_progress_callback,
        encryption_callbacks=encryption_callbacks,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        download_dir=download_dir,
    )


def join_conversation(
    conv_name,
    peer_id,
    others_req_listener,
    data_received_eventhandler=None,
    file_eventhandler=None,
    file_progress_callback=None,
    encryption_callbacks=None,
    timeout_sec=TRANSM_SEND_TIMEOUT_SEC,
    max_retries=TRANSM_REQ_MAX_RETRIES,
    download_dir:str|None=None
):
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
        download_dir (str): the path where received files should be downloaded to
    Returns:
        Conversation: an object through which messages and files can be sent
    """
    return ipfs_client.join_conversation(
        conv_name=conv_name,
        peer_id=peer_id,
        others_req_listener=others_req_listener,
        data_received_eventhandler=data_received_eventhandler,
        file_eventhandler=file_eventhandler,
        file_progress_callback=file_progress_callback,
        encryption_callbacks=encryption_callbacks,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        download_dir=download_dir,
    )


def listen_for_conversations(
     listener_name: str, eventhandler
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
    return ipfs_client.listen_for_conversations(
         listener_name, eventhandler
    )
