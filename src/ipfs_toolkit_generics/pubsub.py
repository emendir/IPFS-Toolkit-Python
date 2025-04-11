from abc import ABC, abstractmethod
class BasePubSub:
    @abstractmethod
    def publish(self, topic, data):
        pass

    @abstractmethod
    def subscribe(self, topic, eventhandler):
        pass

    @abstractmethod
    def peers(self, topic: str):
        pass
class BasePubsubListener:
    pass