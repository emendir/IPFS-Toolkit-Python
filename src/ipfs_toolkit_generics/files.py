from abc import ABC, abstractmethod


class BaseFiles(ABC):
    @abstractmethod
    def publish(self, path: str):
        pass

    @abstractmethod
    def predict_cid(self, path: str):
        pass

    @abstractmethod
    def download(self, cid, dest_path="."):
        pass

    @abstractmethod
    def read(self, cid):
        pass

    @abstractmethod
    def pin(self, cid: str):
        pass

    @abstractmethod
    def unpin(self, cid: str):
        pass

    @abstractmethod
    def remove(self, cid: str):
        pass

    @abstractmethod
    def list_pins(self, cids_only: bool = False, cache_age_s: int = None):
        pass
