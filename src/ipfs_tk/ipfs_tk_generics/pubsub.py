from abc import ABC, abstractmethod
class BasePubSub(ABC):
    @abstractmethod
    def publish(self, topic, data):
        pass

    @abstractmethod
    def subscribe(self, topic, eventhandler):
        pass

    @abstractmethod
    def list_peers(self, topic: str):
        pass
class BasePubsubListener:
    pass