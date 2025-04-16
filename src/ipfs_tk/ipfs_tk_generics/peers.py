from abc import ABC, abstractmethod


class BasePeers(ABC):

    @abstractmethod
    def list_peers(self, ):
        pass

    @abstractmethod
    def connect(self, multiaddr):
        pass

    @abstractmethod
    def find(self, peer_id: str):
        pass

    @abstractmethod
    def is_connected(self, peer_id, ping_count=1):
        pass


class SwarmFiltersUpdateError(Exception):
    def_message = "Failed to add/remove filter"

    def __str__(self):
        return self.def_message