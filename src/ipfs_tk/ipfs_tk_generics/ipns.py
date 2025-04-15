from abc import ABC, abstractmethod


class BaseIpns(ABC):

    @abstractmethod
    def create_ipns_record(self, name: str, type: str = "rsa", size: int = 2048):
        pass

    @abstractmethod
    def update_ipns_record_from_cid(self, record_name: str, cid: str, ttl: str = "24h", lifetime: str = "24h", ** kwargs: ipfshttpclient.client.base.CommonArgs):
        pass

    @abstractmethod
    def update_ipns_record(self, name: str, path, ttl: str = "24h", lifetime: str = "24h"):
        pass

    @abstractmethod
    def resolve_ipns_key(self, ipns_key, nocache=False):
        pass

    @abstractmethod
    def download_ipns_record(self, ipns_key, path="", nocache=False):
        pass

    @abstractmethod
    def read_ipns_record(self, ipns_key, nocache=False):
        pass

    @abstractmethod
    def get_ipns_record_validity(self, ipns_key):
        pass
