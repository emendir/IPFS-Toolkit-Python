from ipfs_api import (
    _start,
    publish,
    download,
    read,
    pin,
    unpin,
    create_ipns_record,
    update_ipns_record_from_cid,
    update_ipns_record,
    resolve_ipns_key,
    download_ipns_record,
    read_ipns_record,
    list_peer_multiaddrs,
    find_peer,
    my_id,
    create_tcp_listening_connection,
    create_tcp_sending_connection,
    close_tcp_sending_connection,
    close_tcp_listening_connection,
    check_peer_connection,
    find_providers,
    pubsub_publish,
    pubsub_subscribe,
    pubsub_peers,
    http_client
)
from termcolor import colored
print(colored("IPFS_API: DEPRECATED: The IPFS_API module has been renamed to ipfs_api.ipfs_api to accord with PEP 8 naming conventions.", "yellow"))

"""Deprecated naming of Functions:"""


def Start():
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Start) has been renamed to ipfs_api._start to accord with PEP 8 naming conventions.", "yellow"))
    return _start()


def PublishToTopic(topic, data):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.PublishToTopic) has been renamed to ipfs_api.pubsub_publish to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_publish(topic, data)


def SubscribeToTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.SubscribeToTopic) has been renamed to ipfs_api.pubsub_subscribe to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_subscribe(topic, eventhandler)


def UnsubscribeFromTopic(topic, eventhandler):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.UnsubscribeFromTopic) has been removed in ipfs_api. Call .terminate() on the returned subscription object instead.", "yellow"))
    return


def TopicPeers(topic: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.TopicPeers) has been renamed to ipfs_api.pubsub_peers to accord with PEP 8 naming conventions.", "yellow"))
    return pubsub_peers(topic)


def UploadFile(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.UploadFile) has been renamed to ipfs_api.publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Upload(filename: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Upload) has been renamed to ipfs_api.publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(filename)


def Publish(path: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Publish) has been renamed to ipfs_api.publish to accord with PEP 8 naming conventions.", "yellow"))
    return publish(path)


def Pin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Pin) has been renamed to ipfs_api.pin to accord with PEP 8 naming conventions.", "yellow"))
    return pin(cid)


def Unpin(cid: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Unpin) has been renamed to ipfs_api.unpin to accord with PEP 8 naming conventions.", "yellow"))
    return unpin(cid)


def Download_file(ID, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Download_file) has been renamed to ipfs_api.download to accord with PEP 8 naming conventions.", "yellow"))
    return download(ID, path)


def Download(cid, path=""):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.Download) has been renamed to ipfs_api.download to accord with PEP 8 naming conventions.", "yellow"))
    return download(cid, path)


def CatFile(ID):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.CatFile) has been renamed to ipfs_api.read to accord with PEP 8 naming conventions.", "yellow"))
    return read(ID)


def CreateIPNS_Record(name: str, type: str = "rsa", size: int = 2048):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.CreateIPNS_Record) has been renamed to ipfs_api.create_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return create_ipns_record(name, type, size)


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.UpdateIPNS_RecordFromHash) has been renamed to ipfs_api.update_ipns_record_from_cid to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record_from_cid(name, cid, ttl, lifetime)


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.UpdateIPNS_Record) has been renamed to ipfs_api.update_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return update_ipns_record(name, path, ttl, lifetime)


def ResolveIPNS_Key(ipns_id, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.ResolveIPNS_Key) has been renamed to ipfs_api.resolve_ipns_key to accord with PEP 8 naming conventions.", "yellow"))
    return resolve_ipns_key(ipns_id, nocache)


def DownloadIPNS_Record(name, path="", nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.DownloadIPNS_Record) has been renamed to ipfs_api.download_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return download_ipns_record(name, path, nocache)


def CatIPNS_Record(name, nocache=False):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.CatIPNS_Record) has been renamed to ipfs_api.read_ipns_record to accord with PEP 8 naming conventions.", "yellow"))
    return read_ipns_record(name, nocache)


def ListPeerMaddresses():
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.ListPeerMaddresses) has been renamed to ipfs_api.list_peer_multiaddrs to accord with PEP 8 naming conventions.", "yellow"))
    return list_peer_multiaddrs()


def FindPeer(ID: str):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.FindPeer) has been renamed to ipfs_api.find_peer to accord with PEP 8 naming conventions.", "yellow"))
    return find_peer(ID)


def MyID():
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.MyID) has been renamed to ipfs_api.my_id to accord with PEP 8 naming conventions.", "yellow"))
    return my_id()


def ListenOnPort(protocol, port):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.ListenOnPort) has been renamed to ipfs_api.create_tcp_listening_connection to accord with PEP 8 naming conventions.", "yellow"))
    http_client.p2p.listen("/x/" + protocol, "/ip4/127.0.0.1/tcp/" + str(port))


listenonport = ListenOnPort
Listen = ListenOnPort
listen = ListenOnPort


def ForwardFromPortToPeer(protocol: str, port, peerID):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.ForwardFromPortToPeer) has been renamed to ipfs_api.create_tcp_sending_connection to accord with PEP 8 naming conventions.", "yellow"))
    http_client.p2p.forward("/x/" + protocol, "/ip4/127.0.0.1/tcp/" +
                            str(port), "/p2p/" + peerID)


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.ClosePortForwarding) has been renamed replaced by the following two functions: ipfs_api.close_tcp_sending_connection and ipfs_api.close_tcp_listening_connection to accord with PEP 8 naming conventions.", "yellow"))
    http_client.p2p.close(all, protocol, listenaddress, targetaddress)


def CheckPeerConnection(id, name=""):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.CheckPeerConnection) has been renamed to ipfs_api.check_peer_connection to accord with PEP 8 naming conventions.", "yellow"))
    return check_peer_connection(id, name)


def FindProviders(cid):
    print(colored("IPFS_API: DEPRECATED: This function (IPFS_API.FindProviders) has been renamed to ipfs_api.find_providers to accord with PEP 8 naming conventions.", "yellow"))
    return find_providers(cid)
