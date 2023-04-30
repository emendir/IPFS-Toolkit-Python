""""""


import time
from threading import Thread
import os
import json
import ipfs_api
from datetime import datetime

SUCCESSIVE_REGISTER_IGNORE_DUR_SEC = 5
CONNECTION_ATTEMPT_INTERVAL_SEC = 300


class Peer:
    """Object for representing an IPFS peer and contact information collected
    from it."""
    __peer_id = None
    __multiaddrs = []     # list((multiaddr, datetime))
    __last_seen = None  # datetime

    def __init__(self, peer_id="", serial=None):
        if peer_id and not serial:
            self.__peer_id = peer_id
        elif serial:
            data = json.loads(serial)
            self.__peer_id = data['peer_id']
            self.__last_seen = string_to_time(data['last_seen'])
            self.__multiaddrs = [(addr, string_to_time(t)) for addr, t in data['multiaddrs']]
        else:
            raise ValueError(
                "You must specify exactly one parameter to this constructor: peer_id OR serial")

    def register_contact_event(self):
        """
        Returns:
            bool: whether or not the event was registered
        """
        # skip registering if last register wasn't very long ago
        if self.last_seen() and (datetime.utcnow() - self.last_seen()).total_seconds() < SUCCESSIVE_REGISTER_IGNORE_DUR_SEC:
            return False

        multiaddrs = ipfs_api.get_peer_multiaddrs(self.__peer_id)
        now = datetime.utcnow()
        if multiaddrs:
            self.__last_seen = now
        else:
            return False

        # update last_seen dates of known multiaddrs, removing them from
        # the local multiaddrs list
        for i, (multiaddr, last_seen) in enumerate(self.__multiaddrs):
            if multiaddr in multiaddrs:
                self.__multiaddrs[i] = (multiaddr, now)
                multiaddrs.remove(multiaddr)

        # add new multiaddrs to known multiaddrs
        for multiaddr in multiaddrs:
            self.__multiaddrs.append((multiaddr, now))
        return True

    def last_seen(self):
        """Returns the date at which this peer was last seen.
        Returns:
            datetime: the date at which this peer was last seen or None
        """
        return self.__last_seen

    def connect(self):
        """Tries to connect to this peer.
        Returns:
            bool: whether or not we managed to connect to this peer
        """
        for multiaddr, date in self.__multiaddrs:
            success = ipfs_api.http_client.swarm.connect(
                f"{multiaddr}/p2p/{self.__peer_id}")
            if success:
                self.register_contact_event()
                return True
        # if none of the known multiaddresses worked, try a general findpeer
        if ipfs_api.find_peer(self.__peer_id):
            self.register_contact_event()
            return True
        return False

    def multiaddrs(self):
        return self.__multiaddrs

    def peer_id(self):
        return self.__peer_id

    def serialise(self):
        data = {
            'peer_id': self.__peer_id,
            'last_seen': time_to_string(self.__last_seen),
            'multiaddrs': [[addr, time_to_string(t)] for addr, t in self.__multiaddrs],
        }
        return json.dumps(data)


class PeerMonitor:
    """A class for managing peer contact information for a certain app"""
    period_hrs = 100
    forget_after_hrs = 200
    __peers = []  # list(Peer)
    __terminate = False

    def __init__(self, filepath):
        self.__filepath = filepath
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                data = json.loads(file.read())
                peers = data['peers']
                for peer_data in peers:
                    self.__peers.append(Peer(serial=peer_data))
        Thread(target=self.connect_to_peers, args=()).start()

    def register_contact_event(self, peer_id):
        peer = self.get_peer_by_id(peer_id)
        if not peer:
            peer = Peer(peer_id)
            self.__peers.append(peer)

        # try register, and if data is recorded, save to file
        if peer.register_contact_event():
            self.save()

    def get_peer_by_id(self, peer_id):
        for peer in self.__peers:
            if peer.peer_id() == peer_id:
                return peer

    def peers(self):
        return self.__peers

    def save(self):
        with open(self.__filepath, 'w+') as file:
            data = {
                'peers': [peer.serialise() for peer in self.__peers]
            }
            file.write(json.dumps(data))

    def connect_to_peers(self):
        while not self.__terminate:
            for peer in self.__peers:
                Thread(target=peer.connect, args=()).start()
            for i in range(CONNECTION_ATTEMPT_INTERVAL_SEC):
                time.sleep(1)
                if self.__terminate:
                    return

    def terminate(self):
        self.__terminate = True


TIME_FORMAT = '%Y.%m.%d_%H.%M.%S'


def time_to_string(time: datetime):
    return time.strftime(TIME_FORMAT)


def string_to_time(string):
    return datetime.strptime(string, TIME_FORMAT)
