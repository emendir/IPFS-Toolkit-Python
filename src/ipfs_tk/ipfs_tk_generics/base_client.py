from abc import ABC, abstractproperty, abstractmethod
from .pubsub import BasePubSub
from .tunnels import BaseTunnels
from .files import BaseFiles


class BaseClient(ABC):
    @abstractproperty
    def files(self) -> BaseFiles:
        pass

    @abstractproperty
    def pubsub(self) -> BasePubSub:
        pass

    @abstractproperty
    def tunnels(self) -> BaseTunnels:
        pass

    @abstractproperty
    def peer_id(self) -> str:
        pass

    @abstractmethod
    def get_addrs(self) -> set[str]:
        pass
    @abstractmethod
    def terminate(self):
        pass