import socket
import time
from ipfs_tk_generics.base_client import BaseClient
from .config import (
    PRINT_LOG_CONNECTIONS,
    BUFFER_SIZE,
    sending_ports,
)

from .errors import (
    IPFS_Error,
)
from typing import Optional, Union


def __add_integritybyte_to_buffer(buffer: bytes) -> bytearray:
    # Adding an integrity byte that equals the sum of all the bytes in the buffer modulus 256
    # to be able to detect data corruption:
    sum = 0
    for byte in buffer:
        sum += byte
        if (
            sum > 65000
        ):  # if the sum is reaching the upper limit of an unsigned 16-bit integer
            sum = (
                sum % 256
            )  # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
    # adding the integrity byte to the start of the buffer
    return bytearray([sum % 256]) + buffer


# turns a base 10 integer into a base 255 integer in  the form of an array of bytes where each byte represents a digit, and where no byte has the value 0
def _to_b255_no_0s(number: int) -> bytearray:
    array = bytearray([])
    while number > 0:
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
    while i >= 0:
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


def _tcp_send_all(sock: socket.socket, data: Union[bytearray, bytes]):
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
                        total_data += data[: data.index(0)]
                        length = _from_b255_no_0s(total_data)
                        total_data = data[data.index(0) + 1 :]
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


def _tcp_recv_buffer_timeout(
    sock: socket.socket, buffer_size: int = BUFFER_SIZE, timeout: int = 5
) -> bytes:
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


def _create_sending_connection(
    ipfs_client: BaseClient, peer_id: str, protocol: str, port: None = None
) -> socket.socket:
    # _close_sending_connection(
    #     peer_id=peer_id, name=protocol)
    if port:
        _close_sending_connection(ipfs_client, port=port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if port == None:
        for prt in sending_ports:  # trying ports until we find a free one
            try:
                ipfs_client.tunnels.open_sender(protocol, prt, peer_id)
                sock.connect((ipfs_client._ipfs_host_ip(), prt))
                return sock
            except (
                Exception
            ) as e:  # ignore errors caused by port already in use
                if "bind: address already in use" not in str(e):
                    raise IPFS_Error(str(e))
                pass
        raise IPFS_Error("Failed to find free port for sending connection")
    else:
        try:
            ipfs_client.tunnels.open_sender(protocol, port, peer_id)
            sock.connect((ipfs_client._ipfs_host_ip(), prt))
            return sock
        except Exception as e:
            raise IPFS_Error(str(e))


def _create_listening_connection(
    ipfs_client: BaseClient, protocol, port, force=True
):
    """
    Args:
        bool force: whether or not already existing conflicting connections should be closed.
    """
    try:
        _close_listening_connection(ipfs_client, name=protocol)
        ipfs_client.tunnels.open_listener(protocol, port)
        if PRINT_LOG_CONNECTIONS:
            print(f'listening as "{protocol}" on {port}')
    except:
        raise IPFS_Error(
            "Error registering listening connection to IPFS: "
            f"/x/{protocol}/ip4/{ipfs_client._ipfs_host_ip()}/udp/{port}"
        )

    return port


def _close_sending_connection(
    ipfs_client: BaseClient,
    peer_id: str | None = None,
    name: str | None = None,
    port: None = None,
):
    try:
        ipfs_client.tunnels.close_sender(peer_id=peer_id, name=name, port=port)
    except Exception as e:
        raise IPFS_Error(str(e))


def _close_listening_connection(
    ipfs_client: BaseClient, name: str | None = None, port: int | None = None
):
    try:
        ipfs_client.tunnels.close_listener(name=name, port=port)
    except Exception as e:
        raise IPFS_Error(str(e))


def disprepend_bytearray_segment(data: bytearray, separator: int):
    part_1 = data[: data.index(separator)]
    part_2 = data[data.index(separator) + 1 :]
    return part_1, part_2
