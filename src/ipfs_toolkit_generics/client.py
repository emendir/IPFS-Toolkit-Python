from abc import ABC, abstractproperty, abstractmethod
from .pubsub import BasePubSub
from .tcp import BaseTcp
from .files import BaseFiles

class BaseClient(ABC):
    @abstractproperty
    def files(self)->BaseFiles:
        pass
    @abstractproperty
    def pubsub(self)->BasePubSub:
        pass
    @abstractproperty
    def tcp(self)->BaseTcp:
        pass
    @abstractproperty
    def peer_id(self)->str:
        pass
    @abstractmethod
    def get_multiaddrs(self)->set[str]:
        pass