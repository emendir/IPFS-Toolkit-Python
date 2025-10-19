from ipfs_tk_generics.client import IpfsClient
from ipfs_tk_generics.tunnels import BaseTunnels, SenderTunnel, ListenerTunnel, TunnelsList

class RemoteTunnels(BaseTunnels):
    def __init__(self, node:IpfsClient):
        self._node = node
        self._http_client = self._node._http_client
        BaseTunnels.__init__(self)
        
    def open_listener(self,name: str, port: int):
        """Open a listener TCP connection for IPFS' libp2p stream-mounting (port-forwarding).
        TCP traffic coming from another peer via this connection is forwarded
        to the specified port on localhost.
        Args:
            name (str): the name of the connection (starts with /x/)
            port (int): the local TCP port number to forward incoming traffic to
        """
        if name[:3] != "/x/":
            name = "/x/" + name
        self._http_client.p2p.listen(
            name, f"/ip4/{self._node._ipfs_host_ip()}/tcp/{port}"
        )

    def open_sender(self, name: str, port, peerID):
        """Open a sending TCP connection for IPFS' libp2p stream-mounting (port-forwarding).
        TCP traffic sent to the specified port on localhost will be fowarded
        to the specified peer via this connection.
        Args:
            name (str): the name of the connection (starts with /x/)
            port (int): the local TCP port number from which to forward traffic
        """
        if name[:3] != "/x/":
            name = "/x/" + name
        self._http_client.p2p.forward(
            name, f"/ip4/{self._node._ipfs_host_ip()}/tcp/{port}",f"/p2p/{peerID}"
        )

    
    def close_all(self, listeners_only=False):
        """Close all libp2p stream-mounting (IPFS port-forwarding) connections.
        Args:
            listeners_only (bool): if set to True, only listening connections are closed
        """
        if listeners_only:
            self._http_client.p2p.close(listenaddress="/p2p/" + my_id())
        else:
            self._http_client.p2p.close(True)

    def close_sender(self, name: str = None, port: str = None, peer_id: str = None):
        """Close specific sending libp2p stream-mounting (IPFS port-forwarding) connections.
        Args:
            name (str): the name of the connection to close
            port (str): the local forwarded TCP port of the connection to close
            peer_id (str): the target peer_id of the connection to close
        """
        if name and name[:3] != "/x/":
            name = "/x/" + name
        if port and isinstance(port, int):
            listenaddress = f"/ip4/{self._node._ipfs_host_ip()}/tcp/{port}"
        else:
            listenaddress = port
        if peer_id and peer_id[:5] != "/p2p/":
            targetaddress = "/p2p/" + peer_id
        else:
            targetaddress = peer_id
        self._http_client.p2p.close(False, name, listenaddress, targetaddress)

    
    def close_listener(self, name: str = None, port: str = None):
        """Close specific listening libp2p stream-mounting (IPFS port-forwarding) connections.
        Args:
            name (str): the name of the connection to close
            port (str): the local listening TCP port of the connection to close
        """
        if name and name[:3] != "/x/":
            name = "/x/" + name
        if port and isinstance(port, int):
            targetaddress = f"/ip4/{self._node._ipfs_host_ip()}/tcp/{port}"
        else:
            targetaddress = port
        self._http_client.p2p.close(False, name, None, targetaddress)



    def get_tunnels(self)->TunnelsList:
        listeners:list[ListenerTunnel]=[]
        senders:list[SenderTunnel]=[]
        my_id=f"/p2p/{self._node.peer_id}"
        for i in self._http_client.p2p.ls()[0]["Listeners"]:
            if i["ListenAddress"] == my_id:
                listeners.append(ListenerTunnel(i["Protocol"], i["TargetAddress"]))
            else:
                senders.append(SenderTunnel(i["Protocol"], i["ListenAddress"], i["TargetAddress"]))
        return TunnelsList(senders, listeners)