from abc import ABC, abstractmethod
class BaseTcp:

    @abstractmethod    
    def open_listener(self, name: str, port: int):
        pass
    @abstractmethod
    def open_sender(self, name: str, port, peerID):
        pass
    @abstractmethod
    def close_all(self, listeners_only=False):
        pass
    @abstractmethod
    def close_sender(self, name: str = None, port: str = None, peer_id: str = None):
        pass
    @abstractmethod
    def close_listener(self, name: str = None, port: str = None):
        pass

