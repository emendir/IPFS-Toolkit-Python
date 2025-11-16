import socket
from time import sleep
import threading
from threading import Thread
from datetime import datetime, timezone
import time
import traceback
from ipfs_tk_generics.base_client import BaseClient

from .errors import (
    InvalidPeer,
    CommunicationTimeout,
    UnreadableReply,
)
from .config import (
    PRINT_LOG,
    PRINT_LOG_CONNECTIONS,
    PRINT_LOG_TRANSMISSIONS,
    TRANSM_REQ_MAX_RETRIES,
    TRANSM_SEND_TIMEOUT_SEC,
    TRANSM_RECV_TIMEOUT_SEC,
    BUFFER_SIZE,
)

from .utils import (
    __add_integritybyte_to_buffer,
    _tcp_send_all,
    _tcp_recv_all,
    _tcp_recv_buffer_timeout,
    _create_sending_connection,
    _create_listening_connection,
    _close_sending_connection,
    _close_listening_connection,
)
from typing import Callable


UTC = timezone.utc


def transmit_data(
    ipfs_client: BaseClient,
    data: bytes,
    peer_id: str,
    req_lis_name: str,
    timeout_sec: int = TRANSM_SEND_TIMEOUT_SEC,
    max_retries: int = TRANSM_REQ_MAX_RETRIES,
):
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
    if peer_id == ipfs_client.peer_id:
        raise InvalidPeer(
            message="You cannot use your own IPFS peer ID as the recipient."
        )

    def SendTransmissionRequest():
        """
        Sends transmission request to the recipient.
        """
        request_data = __add_integritybyte_to_buffer(
            ipfs_client.peer_id.encode()
        )
        tries = 0

        # repeatedly try to send transmission request to recipient until a reply is received
        while max_retries == -1 or tries < max_retries:
            if PRINT_LOG_TRANSMISSIONS:
                print("Sending transmission request to " + str(req_lis_name))
            sock = _create_sending_connection(
                ipfs_client, peer_id, req_lis_name
            )
            # sock.sendall(request_data)
            sock.settimeout(timeout_sec)
            _tcp_send_all(sock, request_data)
            if PRINT_LOG_TRANSMISSIONS:
                print("Sent transmission request to " + str(req_lis_name))

            try:
                # reply = sock.recv(BUFFER_SIZE)
                reply = _tcp_recv_buffer_timeout(
                    sock, BUFFER_SIZE, timeout=timeout_sec
                )
            except socket.timeout:
                sock.close()
                _close_sending_connection(ipfs_client, peer_id, req_lis_name)
                raise CommunicationTimeout(
                    "Received no response from peer while sending transmission request."
                )

            # reply = _tcp_recv_all(sock, timeout_sec)
            # _tcp_recv_all
            sock.close()
            del sock
            _close_sending_connection(ipfs_client, peer_id, req_lis_name)
            if reply:
                try:
                    their_trsm_port = reply[30:].decode()  # signal success
                    if their_trsm_port:
                        if PRINT_LOG_TRANSMISSIONS:
                            print(
                                "Transmission request to "
                                + str(req_lis_name)
                                + "was received."
                            )
                        return their_trsm_port
                    else:
                        raise UnreadableReply()
                except:
                    raise UnreadableReply()
            else:
                if PRINT_LOG_TRANSMISSIONS:
                    print(
                        "Transmission request send "
                        + str(req_lis_name)
                        + "timeout_sec reached."
                    )
            tries += 1
        _close_sending_connection(ipfs_client, peer_id, req_lis_name)
        raise CommunicationTimeout(
            "Received no response from peer while sending transmission request."
        )

    their_trsm_port = SendTransmissionRequest()
    sock = _create_sending_connection(ipfs_client, peer_id, their_trsm_port)
    sock.settimeout(timeout_sec)
    # sock.sendall(data)  # transmit Data
    _tcp_send_all(sock, data)
    if PRINT_LOG_TRANSMISSIONS:
        print("Sent Transmission Data", data)
    response = sock.recv(BUFFER_SIZE)
    if response and response == b"Finished!":
        # conn.close()
        sock.close()
        _close_sending_connection(ipfs_client, peer_id, their_trsm_port)
        if PRINT_LOG_TRANSMISSIONS:
            print(": Finished transmission.")
        return True  # signal success
    else:
        if PRINT_LOG_TRANSMISSIONS:
            print("Received unrecognised response:", response)
        raise UnreadableReply()
    # sock.close()
    # _close_sending_connection(peer_id, their_trsm_port)


def listen_for_transmissions(
    ipfs_client: BaseClient, listener_name: str, eventhandler: Callable
) -> "TransmissionListener":
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
    return TransmissionListener(ipfs_client, listener_name, eventhandler)


class TransmissionListener:
    """
    Listens for incoming transmission requests (senders requesting to transmit
    data to us) and sets up the machinery needed to receive those transmissions.
    Call `.terminate()` on  TransmissionListener objects when you no longer
    need them to clean up IPFS connection configurations.
    """

    # This function itself is called to process the transmission request buffer sent by the transmission sender.
    _terminate = False

    def __init__(
        self,
        ipfs_client: BaseClient,
        listener_name: str,
        eventhandler: Callable,
    ):
        """
        Args:
            listener_name (str): the name of this TransmissionListener (chosen by
                user, allows distinguishing multiple IPFS-DataTransmission-Listeners
                running on the same computer for different applications)
            eventhandler (function): the function that should be called when a transmission of
                data is received.
                Parameters: data (bytearray), peer_id (str)
        """
        self.ipfs_client = ipfs_client
        self._listener_name = listener_name
        self.eventhandler = eventhandler
        self.port = 0  # not yet set
        self._listener = Thread(
            target=self._listen,
            args=(),
            name=f"DataTransmissionListener-{listener_name}",
        )
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
                if (
                    sum > 65000
                ):  # if the sum is reaching the upper limit of an unsigned 16-bit integer
                    sum = (
                        sum % 256
                    )  # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
            # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
            if sum % 256 != integrity_byte:
                if PRINT_LOG:
                    print(
                        self._listener_name
                        + ": Received a buffer with a non-matching integrity buffer"
                    )
                return

            peer_id = data.decode()

            if PRINT_LOG_TRANSMISSIONS:
                print(self._listener_name + ": Received transmission request.")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((self.ipfs_client._ipfs_host_ip(), 0))
            our_port = sock.getsockname()[1]
            _create_listening_connection(
                self.ipfs_client, str(our_port), our_port
            )
            sock.listen()

            listener = Thread(
                target=self._receive_transmission,
                args=(peer_id, sock, our_port, self.eventhandler),
                name=f"DataTransmissionReceiver-{our_port}",
            )
            listener.start()
            return our_port

        except Exception as e:
            print("")
            print(
                self._listener_name
                + ": Exception in NetTerm.ReceiveTransmissions.__receive_transmission_requests()"
            )
            print("----------------------------------------------------")
            traceback.print_exc()  # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print(
                self._listener_name
                + ": Could not decode transmission request."
            )

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
        Thread(
            target=eventhandler,
            args=(data, peer_id),
            name="TransmissionListener.ReceivedTransmission",
        ).start()
        _close_listening_connection(self.ipfs_client, str(our_port), our_port)
        sock.close()

    def _listen(self):
        if PRINT_LOG_TRANSMISSIONS:
            print("Creating Listener")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ipfs_client._ipfs_host_ip(), 0))
        self.port = self.socket.getsockname()[1]
        _create_listening_connection(
            self.ipfs_client, self._listener_name, self.port
        )

        if PRINT_LOG_TRANSMISSIONS:
            print(
                self._listener_name
                + ": Listening for transmission requests as "
                + self._listener_name
            )
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
        if self._terminate:
            return
        self._terminate = True

        # if socket hasn't been initialised yet
        if not self.port:
            return

        _close_listening_connection(
            self.ipfs_client, self._listener_name, self.port
        )

        while self._listener.is_alive():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ipfs_client._ipfs_host_ip(), self.port))
                # sock.sendall("close".encode())
                _tcp_send_all(sock, "close".encode())

                # _tcp_recv_all(sock)
                sock.close()
                del sock
            except Exception as e:
                print("Error closing listener:", e)
                pass
            sleep(0.1)

    def __del__(self):
        self.terminate()


class BufferSender:
    def __init__(self, ipfs_client: BaseClient, peer_id, proto):
        self.ipfs_client = ipfs_client
        self.peer_id = peer_id
        self.proto = proto
        self.sock = _create_sending_connection(
            self.ipfs_client, peer_id, proto
        )

    def send_buffer(self, data):
        try:
            self.sock.send(data)
        except:
            self.sock = _create_sending_connection(
                self.ipfs_client, self.peer_id, self.proto
            )
            self.sock.send(data)

    def terminate(self):
        _close_sending_connection(self.ipfs_client, self.peer_id, self.proto)

    def __del__(self):
        self.terminate()


class BufferReceiver:
    def __init__(
        self,
        ipfs_client: BaseClient,
        eventhandler,
        proto,
        address: tuple[str, int],
        buffer_size=BUFFER_SIZE,
        monitoring_interval=2,
        status_eventhandler=None,
        eventhandlers_on_new_threads=True,
    ):
        self.ipfs_client = ipfs_client
        self.proto = proto
        self._listener = _ListenerTCP(
            eventhandler,
            address,
            buffer_size=buffer_size,
            monitoring_interval=monitoring_interval,
            status_eventhandler=status_eventhandler,
            eventhandlers_on_new_threads=eventhandlers_on_new_threads,
        )
        _create_listening_connection(
            self.ipfs_client, proto, self._listener.port
        )

    def terminate(self):
        _close_listening_connection(
            self.ipfs_client, self.proto, self._listener.port
        )
        self._listener.terminate()

    def __del__(self):
        self.terminate()


def listen_to_buffers(
    ipfs_client: BaseClient,
    eventhandler,
    proto,
    ip_addr="127.0.0.1",
    buffer_size=BUFFER_SIZE,
    monitoring_interval=2,
    status_eventhandler=None,
    eventhandlers_on_new_threads=True,
):
    return BufferReceiver(
        ipfs_client,
        eventhandler,
        proto,
        (ip_addr, 0),
        buffer_size=buffer_size,
        monitoring_interval=monitoring_interval,
        status_eventhandler=status_eventhandler,
        eventhandlers_on_new_threads=eventhandlers_on_new_threads,
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
    last_time_recv = datetime.now(UTC)

    def __init__(
        self,
        eventhandler,
        address=tuple[int, str],
        buffer_size=BUFFER_SIZE,
        monitoring_interval=2,
        status_eventhandler=None,
        eventhandlers_on_new_threads=True,
    ):
        threading.Thread.__init__(self)
        self.address = address
        self.name = f"TCPListener-{self.address}"
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size
        self.eventhandlers_on_new_threads = eventhandlers_on_new_threads
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.bind(self.address)
        # in case it had been 0 (requesting automatic port assiggnent)
        self.port = self.sock.getsockname()[1]

        if status_eventhandler is not None:
            self.status_eventhandler = status_eventhandler
            self.monitoring_interval = monitoring_interval
            self.last_time_recv = datetime.now(UTC)
            self.status_monitor_thread = Thread(
                target=self.status_monitor,
                args=(),
                name="ListenerTP.status_monitor",
            )
            self.status_monitor_thread.start()

        self.start()

        if PRINT_LOG_CONNECTIONS:
            print("Created listener.")

    def run(self):
        self.sock.listen(1)
        conn, ip_addr = self.sock.accept()

        while True:
            data = conn.recv(self.buffer_size)
            self.last_time_recv = datetime.now(UTC)
            if self._terminate == True:
                if PRINT_LOG_CONNECTIONS:
                    print("listener terminated")
                break
            if not data:
                if PRINT_LOG_CONNECTIONS:
                    print("received null data")
                # break
            if len(data) > 0:
                if self.eventhandlers_on_new_threads:
                    ev = Thread(
                        target=self.eventhandler,
                        args=(data,),
                        name="TCPListener-eventhandler",
                    )
                    ev.start()
                else:
                    self.eventhandler(data)
        conn.close()
        self.sock.close()
        if PRINT_LOG_CONNECTIONS:
            print("Closed listener.")

    def status_monitor(self):
        while True:
            if self._terminate:
                break
            time.sleep(self.monitoring_interval)
            if (
                datetime.now(UTC) - self.last_time_recv
            ).total_seconds() > self.monitoring_interval:
                self.status_eventhandler(
                    (datetime.now(UTC) - self.last_time_recv).total_seconds()
                )

    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    # thread = _thread.start_new_thread(ListenIndefinately,())

    # return thread, used_port

    def terminate(self):
        if self._terminate:
            return
        if PRINT_LOG_CONNECTIONS:
            print("terminating listener")
        self._terminate = True  # marking the terminate flag as true
        self.sock.close()

    def __del__(self):
        self.terminate()


def listen_to_buffers_on_port(
    ipfs_client: BaseClient,
    eventhandler,
    proto,
    address: tuple[str, int],
    buffer_size=BUFFER_SIZE,
    monitoring_interval=2,
    status_eventhandler=None,
):
    return BufferReceiver(
        ipfs_client,
        eventhandler,
        proto,
        address,
        buffer_size,
        monitoring_interval,
        status_eventhandler,
    )
