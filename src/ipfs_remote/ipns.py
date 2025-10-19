from ipfs_tk_generics.client import IpfsClient
from ipfs_tk_generics.ipns import BaseIpns
from . import ipfshttpclient2 as ipfshttpclient
from datetime import datetime
import os
import shutil
import tempfile

class RemoteIpns(BaseIpns):
    def __init__(self, node: IpfsClient):
        self._node = node
        self._self._http_client = self._node._http_client

    def create_ipns_record(self, name: str, type: str = "rsa", size: int = 2048):
        """Create an IPNS record (eqv. IPNS key).
        Args:
            name (str): the name of the record/key (in the scope of this IPFS node)
            type (str): the cryptographic algorithm behind this key's security
            size (int): the length of the key
        """
        result = self._http_client.key.gen(key_name=name, type=type, size=size)
        if isinstance(result, list):
            return result[-1]["Id"]
        else:
            return result["Id"]

    def update_ipns_record_from_cid(self, record_name: str, cid: str, ttl: str = "24h", lifetime: str = "24h", ** kwargs: ipfshttpclient.client.base.CommonArgs):
        """Assign IPFS content to an IPNS record.
        Args:
            record_name (str): the name of the IPNS record (IPNS key) to be updated
            cid (str): the IPFS content ID (CID) of the content to assign to the IPNS record
            ttl (str): Time duration this record should be cached for.
                                    Uses the same syntax as the lifetime option.
                                    (caution: experimental).
            lifetime (str): Time duration that the record will be valid for.
                                    Default: 24h.
        """
        self._http_client.name.publish(ipfs_path=cid, key=record_name,
                                       ttl=ttl, lifetime=lifetime, ** kwargs)

    def update_ipns_record(self, name: str, path, ttl: str = "24h", lifetime: str = "24h"):
        """Publish a file to IPFS and assign it to an IPNS record.
        Args:
            record_name (str): the name of the IPNS record (IPNS key) to be updated
            path (str): the path of the file to assign to the IPNS record
            ttl (str): Time duration this record should be cached for.
                                    Uses the same syntax as the lifetime option.
                                    (caution: experimental).
            lifetime (str): Time duration that the record will be valid for.
                                    Default: 24h.
        """
        cid = self._node.files.publish(path)
        self.update_ipns_record_from_cid(name, cid, ttl=ttl, lifetime=lifetime)
        return cid

    def resolve_ipns_key(self, ipns_key, nocache=False):
        """Get the IPFS CID of the given IPNS record (IPNS key)
        Args:
            ipns_key: the key of the IPNS record to lookup
            nocache: whether or not to ignore this IPFS nodes cached memory of IPNS keys
        Returns:
            str: the IPFS CID associated with the IPNS key
        """
        return self._http_client.name.resolve(name=ipns_key, nocache=nocache)["Path"]

    def download_ipns_record(self, ipns_key, path="", nocache=False):
        """Get the specified IPFS content, saving it to a file.
        Args:
            ipns_key (str): the key of the IPNS record to get
            path (str): (optional) the path (directory or filepath) of the saved file
            nocache: whether or not to ignore this IPFS nodes cached memory of IPNS keys
        """
        return self._node.files.download(self.resolve_ipns_key(ipns_key, nocache=nocache), path)

    def read_ipns_record(self, ipns_key, nocache=False):
        """Returns the textual content of the specified IPFS resource.
        Args:
            ipns_key (str): the key of the IPNS record to read
        Returns:
            str: the content of the specified IPFS resource as text
        """
        return self.files.read(self.resolve_ipns_key(ipns_key, nocache=nocache))

    def get_ipns_record_validity(self, ipns_key):
        """Gets the time at which the given IPNS record expires.

        Args:
            ipns_key (str): the key of the IPNS record to look up

        Returns:
            datetime: the time at which the given IPNS record expires
        """
        if not ipns_key.startswith('/ipns/'):
            ipns_key = f"/ipns/{ipns_key}"
        tempdir = tempfile.mkdtemp()
        record_filepath = os.path.join(tempdir, "ipns_record")
        self._http_client.routing.get(
            ipns_key,
            record_filepath
        )
        response = self._http_client.name.inspect(record_filepath)
        timestamp = response['Entry']['Validity']

        shutil.rmtree(tempdir)
        return datetime.fromisoformat(timestamp[:-1])
