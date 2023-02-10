from ipfs_api import (
    start,
    publish,
    download,
    read,
    pin,
    unpin,
    create_ipns_record,
    update_ipns_record_from_hash,
    update_ipns_record,
    resolve_ipns_key,
    download_ipns_record,
    read_ipns_record,
    list_peer_multiaddrs,
    find_peer,
    my_id,
    listen_on_port,
    forward_from_port_to_peer,
    close_port_forwarding,
    check_peer_connection,
    find_providers,
    pubsub_publish,
    pubsub_subscribe,
    pubsub_unsubscribe,
    pubsub_peers
)
from termcolor import colored
print(colored("IPFS_API: DEPRECATED: The IPFS_API module has been renamed to ipfs_api to accord with PEP 8 naming conventions.", "yellow"))

"""Deprecated naming of Functions:"""


def Start():
    print(colored("IPFS_API: DEPRECATED: This function (start) has been renamed to Start to accord with PEP 8 naming conventions.", "yellow"))
    return start()


def PublishToTopic(topic, data):
    print(colored("IPFS_API: DEPRECATED: This function (PublishToTopic) has been renamed to pubsub_publish to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_publish(topic, data)


def SubscribeToTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (SubscribeToTopic) has been renamed to pubsub_subscribe to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_subscribe(topic, eventhandler)


def UnsubscribeFromTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (UnsubscribeFromTopic) has been renamed to pubsub_unsubscribe to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_unsubscribe(topic, eventhandler)


def TopicPeers(topic: str):
    print(colored("IPFS_API: DEPRECATED: This function (TopicPeers) has been renamed to pubsub_peers to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_peers(topic)


def UploadFile(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (UploadFile) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Upload(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (Upload) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Publish(path: str):
    print(colored("IPFS_API: DEPRECATED: This function (Publish) has been renamed to publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(path)


def Pin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (Pin) has been renamed to pin to accord with PEP 8 naming conventions.", "yellow"))
    return pin(cid)


def Unpin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (Unpin) has been renamed to unpin to accord with PEP 8 naming conventions.", "yellow"))
    return unpin(cid)


def Download_file(ID, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (Download_file) has been renamed to download to accord with PEP 8 naming conventions.", "yellow"))
    return download(ID, path)


def Download(cid, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (Download) has been renamed to download to accord with PEP 8 naming conventions.", "yellow"))
    return download(cid, path)


def CatFile(ID):
    print(colored("IPFS_API: DEPRECATED: This function (CatFile) has been renamed to read to accord with PEP 8 naming conventions.", "yellow"))
    return read(ID)


def CreateIPNS_Record(name: str, type: str = "rsa", size: int = 2048):
    print(colored("IPFS_API: DEPRECATED: This function (CreateIPNS_Record) has been renamed to create_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return create_ipns_record(name, type, size)


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (UpdateIPNS_RecordFromHash) has been renamed to update_ipns_record_from_hash to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record_from_hash(name, cid, ttl, lifetime)


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (UpdateIPNS_Record) has been renamed to update_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record(name, path, ttl, lifetime)


def ResolveIPNS_Key(ipns_id, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (ResolveIPNS_Key) has been renamed to resolve_ipns_key to accord with PEP 8 naming conventions.", "yellow"))
    return resolve_ipns_key(ipns_id, nocache)


def DownloadIPNS_Record(name, path="", nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (DownloadIPNS_Record) has been renamed to download_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return download_ipns_record(name, path, nocache)


def CatIPNS_Record(name, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (CatIPNS_Record) has been renamed to read_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return read_ipns_record(name, nocache)


def ListPeerMaddresses():
    print(colored("IPFS_API: DEPRECATED: This function (ListPeerMaddresses) has been renamed to list_peer_multiaddrs to accord with PEP 8 naming conventions.", "yellow"))
    return list_peer_multiaddrs()


def FindPeer(ID: str):
    print(colored("IPFS_API: DEPRECATED: This function (FindPeer) has been renamed to find_peer to accord with PEP 8 naming conventions.", "yellow"))
    return find_peer(ID)


def MyID():
    print(colored("IPFS_API: DEPRECATED: This function (MyID) has been renamed to my_id to accord with PEP 8 naming conventions.", "yellow"))
    return my_id()


def ListenOnPort(protocol, port):
    print(colored("IPFS_API: DEPRECATED: This function (ListenOnPort) has been renamed to listen_on_port to accord with PEP 8 naming conventions.", "yellow"))
    return listen_on_port(protocol, port)


def ForwardFromPortToPeer(protocol: str, port, peerID):
    print(colored("IPFS_API: DEPRECATED: This function (ForwardFromPortToPeer) has been renamed to forward_from_port_to_peer to accord with PEP 8 naming conventions.", "yellow"))
    return forward_from_port_to_peer(protocol, port, peerID)


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    print(colored("IPFS_API: DEPRECATED: This function (ClosePortForwarding) has been renamed to close_port_forwarding to accord with PEP 8 naming conventions.", "yellow"))
    return close_port_forwarding(all, protocol, listenaddress, targetaddress)


def CheckPeerConnection(id, name=""):
    print(colored("IPFS_API: DEPRECATED: This function (CheckPeerConnection) has been renamed to check_peer_connection to accord with PEP 8 naming conventions.", "yellow"))
    return check_peer_connection(id, name)


def FindProviders(cid):
    print(colored("IPFS_API: DEPRECATED: This function (FindProviders) has been renamed to find_providers to accord with PEP 8 naming conventions.", "yellow"))
    return find_providers(cid)
