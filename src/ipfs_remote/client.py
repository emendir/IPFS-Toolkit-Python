from time import sleep
from ipfs_tk_generics.client import IpfsClient
from .files import RemoteFiles
from .pubsub import RemotePubSub
from .tunnels import RemoteTunnels
from .peers import RemotePeers
from . import ipfshttpclient2 as ipfshttpclient
from base64 import urlsafe_b64decode, urlsafe_b64encode
import socket
from urllib.parse import ParseResult
from urllib.parse import urlparse


class IpfsRemote(IpfsClient):
    def __init__(self, *args, **kwargs):
        self._http_client = ipfshttpclient.client.Client(*args, **kwargs)

        self._pubsub = RemotePubSub(self)
        self._tunnels = RemoteTunnels(self)
        self._files = RemoteFiles(self)
        self._peers = RemotePeers(self)

    @property
    def tunnels(self) -> RemoteTunnels:
        return self._tunnels

    @property
    def pubsub(self) -> RemotePubSub:
        return self._pubsub

    @property
    def files(self) -> RemoteFiles:
        return self._files

    @property
    def peers(self) -> RemotePeers:
        return self._peers

    def _ipfs_api_url(self) -> ParseResult:
        url = self._http_client._client._base_url
        return urlparse(url)

    def _ipfs_host_ip(self) -> str:
        ip_address = socket.gethostbyname(self._ipfs_api_url().hostname)
        return ip_address

    @property
    def peer_id(self):
        """Returns this IPFS node's peer ID.
        Returns:
            str: the peer ID of this node
        """
        return self._http_client.id()["ID"]

    def is_ipfs_running(self):
        """Checks whether or not the IPFS daemon is currently running.
        Returns:
            bool: whether or not the IPFS daemon is currently running
        """
        return len(self.get_addrs()) > 0

    def get_addrs(self):
        """Returns this IPFS node's peer ID.
        Returns:
            str: the peer ID of this node
        """
        return self._http_client.id()["Addresses"]

    def wait_till_ipfs_is_running(self, timeout_sec=None):
        """Waits till it can connect to the local IPFS daemon's HTTP-interface.
        Args:
            timeout_sec (int): maximum time to wait for. If this duration is,
                                exceeded, a TimeoutError is raised.
        """
        count = 0
        while True:
            try:
                if self.is_ipfs_running():
                    return
            except ipfshttpclient.exceptions.ConnectionError as error:
                pass
            sleep(1)
            count += 1
            if timeout_sec and count == timeout_sec:
                raise TimeoutError()

    def terminate(self):
        pass
