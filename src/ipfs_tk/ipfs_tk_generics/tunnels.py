from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
@dataclass
class SenderTunnel:
    name:str
    listen_address:str
    target_address:str
@dataclass
class ListenerTunnel:
    name:str
    target_address:str
@dataclass
class TunnelsList:
    senders:list[SenderTunnel]
    listeners:list[ListenerTunnel]
class BaseTunnels(ABC):
    def __init__(self):
        self._generated_protos:list[str] = []
        self._proto_generator_lock = Lock()
        self._base_init_called = True
    def __init_subclass__(cls, **kwargs):
        orig_init = cls.__init__

        def wrapped_init(self, *args, **kwargs):
            self._base_init_called = False
            orig_init(self, *args, **kwargs)
            if not getattr(self, '_base_init_called', False):
                raise RuntimeError(f"{cls.__name__}.__init__ must call super().__init__()")
        cls.__init__ = wrapped_init
        super().__init_subclass__(**kwargs)
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
    @abstractmethod
    def get_tunnels(self)->TunnelsList:
        pass
    def generate_name(self, prefix:str=""):
        with self._proto_generator_lock:
            tunnels = self.get_tunnels()
            tunnel_names = [
                tunnel.name for tunnel in tunnels.listeners + tunnels.senders
            ]
            new_name= get_new_string(
                self._generated_protos + tunnel_names,
                 prefix
             )
            self._generated_protos.append(new_name)
            return new_name
from random import randint

def get_new_string(existing_strings: list[str], prefix: str) -> str:
    """Return a new string that is not yet in `existing_strings`.

    The new string will start with the specified prefix, appended by the
    shortest possible sequence of letters and digits to make the new string unique.
    """
    existing_set = set(existing_strings)

    i = randint(0, 999999999999)
    while True:
        candidate = f"{prefix}_{i}"
        if candidate not in existing_set:
            return candidate
        i += 1