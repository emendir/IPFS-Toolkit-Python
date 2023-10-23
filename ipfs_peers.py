""""""


from threading import Event
import threading
import time
from threading import Thread, Lock
import os
import json
import ipfs_api
from datetime import datetime, timedelta

# default values for various settings, can all be overridden
FORGET_AFTER_HOURS = 200
SUCCESSIVE_REGISTER_IGNORE_DUR_SEC = 60
CONNECTION_ATTEMPT_INTERVAL_SEC = 5


class Peer:
    """Object for representing an IPFS peer and contact information collected
    from it."""
    __peer_id = None
    __multiaddrs = []     # list((multiaddr, datetime))
    __last_seen = None  # datetime

    __multi_addrs_lock = Lock()
    __terminate = False

    def __init__(self, peer_id="", serial=None):
        if peer_id and not serial:
            self.__peer_id = peer_id
        elif serial:
            if isinstance(serial, str):
                data = json.loads(serial)
            else:
                data = serial
            if not isinstance(serial, dict):
                raise TypeError(
                    f"Parameter serial must be of type dict or str, not {type(serial)}")

            self.__peer_id = data['peer_id']
            self.__last_seen = string_to_time(data['last_seen'])
            self.__multiaddrs = [(addr, string_to_time(t))
                                 for addr, t in data['multiaddrs']]
        else:
            raise ValueError(
                "You must specify exactly one parameter to this constructor: peer_id OR serial")

    def register_contact_event(self, successive_register_ignore_dur_sec=SUCCESSIVE_REGISTER_IGNORE_DUR_SEC):
        """
        Returns:
            bool: whether or not the event was registered
        """
        # skip registering if last register wasn't very long ago
        if self.last_seen() and (datetime.utcnow() - self.last_seen()).total_seconds() < successive_register_ignore_dur_sec:
            return False
        with self.__multi_addrs_lock:
            multiaddrs = ipfs_api.get_peer_multiaddrs(self.__peer_id)
            if not ipfs_api.is_peer_connected(self.__peer_id):
                return False
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

    def forget_old_entries(self, date):
        with self.__multi_addrs_lock:
            indeces_to_delete = []

            # redefine self.__multiaddrs, selecting only those old entries that have the correct date
            self.__multiaddrs = [(multiaddr, last_seen)
                                 for multiaddr, last_seen in self.__multiaddrs if last_seen > date]

    def last_seen(self):
        """Returns the date at which this peer was last seen.
        Returns:
            datetime: the date at which this peer was last seen or None
        """
        return self.__last_seen

    def connect(self, successive_register_ignore_dur_sec=SUCCESSIVE_REGISTER_IGNORE_DUR_SEC):
        """Tries to connect to this peer.
        Returns:
            bool: whether or not we managed to connect to this peer
        """
        for multiaddr, date in self.__multiaddrs:
            if self.__terminate:
                return False
            success = ipfs_api.connect_to_peer(
                f"{multiaddr}/p2p/{self.__peer_id}")
            if success and ipfs_api.is_peer_connected(self.__peer_id):
                self.register_contact_event(successive_register_ignore_dur_sec)

                return True
            if self.__terminate:
                return False
        # if none of the known multiaddresses worked, try a general findpeer
        if ipfs_api.find_peer(self.__peer_id) and ipfs_api.is_peer_connected(self.__peer_id):
            self.register_contact_event(successive_register_ignore_dur_sec)
            return True
        return False

    def multiaddrs(self):
        return self.__multiaddrs

    def peer_id(self):
        return self.__peer_id

    def serialise(self):
        last_seen = None
        last_seen = time_to_string(self.__last_seen)
        data = {
            'peer_id': self.__peer_id,
            'last_seen': last_seen,
            'multiaddrs': [[addr, time_to_string(t)] for addr, t in self.__multiaddrs],
        }
        return data

    def terminate(self):
        self.__terminate = True


class PeerMonitor:
    """A class for managing peer contact information for a certain app
    Args:
        filepath (str): path of the configuration file in which this
                PeerMonitor's data is/should be stored
        forget_after_hrs (int): after how many hours of no communication
                a peer should be forgotten
        connection_attempt_interval_sec (int): in the loop that constantly
                tries to connect to known peers, how many seconds should be
                paused between consecutive connection attempts
        successive_register_ignore_dur_sec (int): minimum duration between
                successive registrations of the same peer
    """
    forget_after_hrs = FORGET_AFTER_HOURS
    connection_attempt_interval_sec = CONNECTION_ATTEMPT_INTERVAL_SEC
    successive_register_ignore_dur_sec = SUCCESSIVE_REGISTER_IGNORE_DUR_SEC
    __peers = []  # list(Peer)
    __terminate = False
    __save_lock = Lock()
    __file_manager_thread = None    # Thread
    __save_event = Event()
    __peers_lock = Lock()   # for adding & removing peers

    def __init__(self,
                 filepath,
                 forget_after_hrs=FORGET_AFTER_HOURS,
                 connection_attempt_interval_sec=CONNECTION_ATTEMPT_INTERVAL_SEC,
                 successive_register_ignore_dur_sec=SUCCESSIVE_REGISTER_IGNORE_DUR_SEC):
        self.__filepath = filepath
        self.forget_after_hrs = forget_after_hrs
        self.connection_attempt_interval_sec = connection_attempt_interval_sec
        self.successive_register_ignore_dur_sec = successive_register_ignore_dur_sec

        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                data = file.read()
            if data.strip("\n"):    # if file isn't empty
                data = json.loads(data)
                peers = data['peers']
                for peer_data in peers:
                    if self.get_peer_by_id(peer_data['peer_id']):
                        # TODO how to warn user about duplicate entries?
                        # Function to merge peers?
                        # Ever necessary?
                        continue
                    self.__peers.append(Peer(serial=peer_data))
        self.__peer_finder_thread = Thread(target=self.__connect_to_peers, args=(),
                                           name="PeerMonitor.__connect_to_peers")
        self.__peer_finder_thread.start()
        self.__file_manager_thread = Thread(
            target=self.__file_manager, args=(), name="PeerMonitor.__file_manager")
        self.__file_manager_thread.start()

    def register_contact_event(self, peer_id):
        # get peer, create if new
        with self.__peers_lock:
            peer = self.get_peer_by_id(peer_id, already_locked=True)
            if not peer:
                peer = Peer(peer_id)
                self.__peers.append(peer)

        # try register, and if data is recorded, save to file
        if peer.register_contact_event(successive_register_ignore_dur_sec=self.successive_register_ignore_dur_sec):
            self.save()

    def get_peer_by_id(self, peer_id, already_locked=False):
        if not already_locked:

            self.__peers_lock.acquire()

        found_peer = None
        for peer in self.__peers:
            if peer.peer_id() == peer_id:
                found_peer = peer
                break
        if not already_locked:
            self.__peers_lock.release()

        return found_peer

    def peers(self):
        return self.__peers
    __save = False

    def __file_manager(self):
        while True:
            if self.__terminate:
                return
            # if self.__save_event.wait(1):
            #     self.save()
            #     self.__save_event.clear()
            if self.__save:
                self.save()
                self.__save = False
            time.sleep(1)

    def save(self):
        if threading.current_thread().name != "PeerMonitor.__file_manager":
            self.__save = True
            return
        with self.__save_lock:
            with open(self.__filepath, 'w+') as file:
                data = {
                    'peers': [peer.serialise() for peer in self.__peers]
                }
                file.write(json.dumps(data))
        # self.__save_event.clear()
        self.__save = False

    def __connect_to_peers(self):
        while not self.__terminate:
            # try to connect to all peers on separate threads
            for peer in self.__peers:
                # Thread(target=peer.connect, args=(self.successive_register_ignore_dur_sec,),
                #        name="PeerMonitor-Peer.connnect").start()
                peer.connect(self.successive_register_ignore_dur_sec)
                # wait a bit to save processing power
                # and reduce up congestion of ipfs http client
                for i in range(self.connection_attempt_interval_sec):
                    if self.__terminate:
                        self.save()
                        return
                    time.sleep(1)

            # make peers forget old multiaddresses
            threshhold_time = datetime.utcnow() - timedelta(hours=self.forget_after_hrs)
            for peer in self.__peers:
                peer.forget_old_entries(threshhold_time)
            # forget old peers
            with self.__peers_lock:
                self.__peers = [
                    peer for peer in self.__peers if peer.multiaddrs()]

            self.save()

    def find_all_peers(self):
        """Try to connect to all peers now.
        Blocks until all connection attempts have been finished."""
        threads = []
        for peer in self.__peers:
            thread = Thread(target=peer.connect, args=(self.successive_register_ignore_dur_sec,))
            threads.append(thread)
            thread.start()
        # wait for all threads to finish
        for thread in threads:
            thread.join()

    def terminate(self, wait=False):
        """Stop this PeerMonitor's activities.
        Args:
            wait (bool): whether or not this function should block until all
                activity has been stopped and resources have been cleaned up
        """

        self.__terminate = True
        for peer in self.__peers:
            peer.terminate()

        self.__peer_finder_thread.join()
        self.__file_manager_thread.join()


TIME_FORMAT = '%Y.%m.%d_%H.%M.%S'


def time_to_string(_time: datetime):
    if not _time:
        return None
    return _time.strftime(TIME_FORMAT)


def string_to_time(string):
    if not string:
        return None
    return datetime.strptime(string, TIME_FORMAT)
