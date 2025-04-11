from ipfs_toolkit_generics.peers import SwarmFiltersUpdateError
from ipfs_toolkit_generics import BaseClient, BasePeers

import ipfshttpclient2 as ipfshttpclient


class RemotePeers(BasePeers):
    def __init__(self, node: BaseClient):
        self._node = node
        self._http_client = self._node._http_client

    def list(self, ):
        """Returns a list of the IPFS multiaddresses of the other nodes
        this node is connected to.
        Returns:
            list(str): a list of the IPFS multiaddresses of the other nodes
            this node is connected to
        """
        return [
            peer['Addr'] + "/" + peer['Peer']
            for peer in self._http_client.swarm.peers()["Peers"]
        ]

    def get_peer_multiaddrs(self, peer_id):
        """Returns the multiaddresses (without the IPFS CID) via which we can reach
        the specified peer.
        Append /p2p/PEER_ID to these multiaddress parts to turn them into complete
        multiaddresses.

        Args:
            peer_id (str): the IPFS ID of the peer to lookup

        Returns:
            list(str): the multiaddresses (without the IPFS CID) via which we can
            reach the given peer
        """
        try:
            response = self._http_client.routing.findpeer(peer_id)
            return response["Responses"][0]["Addrs"]
        except:
            return []

    def connect_to_peer(self, multiaddr):
        """Tries to connect to a peer given its multiaddress.
        Returns:
            bool: success
        """
        try:
            response = self._http_client.swarm.connect(multiaddr)
            if response["Strings"][0][-7:] == "success":
                return True
            return False
        except:
            return False

    def find_peer(self, peer_id: str):
        """Try to connect to the specified IPFS node.
        Args:
            peer_id (str): the IPFS peer ID of the node to connect to
        Returns:
            str: the multiaddress of the connected node
        """
        try:
            response = self._http_client.routing.findpeer(peer_id)
            if (len(response["Responses"][0]["Addrs"]) > 0):
                return response
        except:
            return None

    def is_peer_connected(self, peer_id, ping_count=1):
        """Tests the connection to the given IPFS peer.
        Args:
            peer_id (str): the IPFS ID of the peer to test
            count (int): (optional, default 1) the number of pings to send
        Returns:
            bool: whether or not the peer is connected
        """
        responses = self._http_client.ping(peer_id, count=ping_count)
        return responses[-1]['Success']

    def add_swarm_filter(self, filter_multiaddr):
        try:
            self._http_client.swarm.filters.add(filter_multiaddr)
        except self._ipfshttpclient.exceptions.ErrorResponse:
            # this error always gets thrown, isn't a problem
            pass
        if filter_multiaddr not in self.get_swarm_filters():
            raise SwarmFiltersUpdateError()

    def rm_swarm_filter(self, filter_multiaddr):
        try:
            self._http_client.swarm.filters.rm(filter_multiaddr)
        except ipfshttpclient.exceptions.ErrorResponse:
            # this error always gets thrown, isn't a problem
            pass
        if filter_multiaddr in self.get_swarm_filters():
            raise SwarmFiltersUpdateError()

    def get_swarm_filters(self, ):
        _filters = dict(self._http_client.swarm.filters.list())['Strings']
        return set(_filters) if _filters is not None else set()
