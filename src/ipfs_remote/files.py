from . import ipfshttpclient2 as ipfshttpclient

import os.path
import os
import tempfile
import shutil
from datetime import datetime, timezone
from ipfs_tk_generics.client import IpfsClient
from ipfs_tk_generics.files import BaseFiles


from cachetools import LRUCache
import sys

UTC = timezone.utc


def _is_pypy() -> bool:
    return hasattr(sys, "pypy_version_info")


# we sometime get an error when using pypy instead of cpython
USE_IPFS_CONTENT_CACHE = not _is_pypy()
MAX_CACHE_SIZE = 400 * 1024 * 1024  # 50 MB limit

# Define a custom function to measure the size of cache entries


def _getsizeof_cache_entry(value):
    return sys.getsizeof(value)


class RemoteFiles(BaseFiles):
    def __init__(self, node: IpfsClient):
        self._node = node
        self._http_client = self._node._http_client
        # LRUCache with a custom size-based eviction policy
        self.ipfs_content_cache = LRUCache(
            maxsize=MAX_CACHE_SIZE, getsizeof=_getsizeof_cache_entry
        )
        self.__pins_cache = {}

    def _add_cached_content(self, cid: str, data: bytes):
        if not USE_IPFS_CONTENT_CACHE:
            return
        if sys.getsizeof(data) > MAX_CACHE_SIZE:
            return  # Prevent adding overly large files
        # Cache with auto-eviction based on size
        self.ipfs_content_cache[cid] = data

    def _get_cached_content(self, cid: str) -> bytes | None:
        return self.ipfs_content_cache.get(cid, None)

    def publish(self, path: str):
        """Upload a file or a directory to IPFS, returning its CID.
        Args:
            path (str): the path of the file or directroy to publish
        Returns:
            str: the IPFS content ID (CID) of the published file/directory
        """
        result = self._http_client.add(path, recursive=True)
        if type(result) == list:
            hash = result[-1]["Hash"]
        else:
            hash = result["Hash"]
        return hash

    def predict_cid(self, path: str):
        """Get the CID a file or directory would have if it were to be published on
        IPFS, without actually publishing it.
        Args:
            path (str): the path of the file or directroy to publish
        Returns:
            str: the IPFS content ID (CID) the file/directory would have
                    if published
        """
        result = self._http_client.add(path, recursive=True, only_hash=True)
        if type(result) == list:
            return result[-1]["Hash"]
        else:
            return result["Hash"]

    def download(self, cid, dest_path="."):
        """Get the specified IPFS content, saving it to a file.
        Args:
            cid (str): the IPFS content ID (cid) of the resource to get
            path (str): (optional) the path (directory or filepath) of the saved file
        """

        # create temporary download directory
        tempdir = tempfile.mkdtemp()

        # download and save file/folder to temporary directory
        self._http_client.get(cid=cid, target=tempdir)

        # move file/folder from temporary directory to desired path
        shutil.move(os.path.join(tempdir, cid), dest_path)

        # cleanup temporary directory
        shutil.rmtree(tempdir)

    def read(self, cid: str, nocache: bool = not USE_IPFS_CONTENT_CACHE):
        """Returns the textual content of the specified IPFS resource.
        Args:
            cid (str): the IPFS content ID (CID) of the resource to read
        Returns:
            str: the content of the specified IPFS resource as text
        """
        if not nocache:
            cached_data = self._get_cached_content(cid)
            if cached_data:
                # print("Returning cached data!")
                return cached_data

        data = self._http_client.cat(cid)
        if not nocache:
            self._add_cached_content(cid, data)

        return data

    def pin(self, cid: str):
        """Ensure the specified IPFS resource remains available on this IPFS node.
        Args:
            cid (str): the IPFS content ID (CID) of the resource to pin
        """
        self._http_client.pin.add(cid)

    def unpin(self, cid: str):
        """Allow a pinned IPFS resource to be garbage-collected and removed on this IPFS node.
        Args:
            cid (str): the IPFS content ID (CID) of the resource to unpin
        """
        self._http_client.pin.rm(cid)

    def remove(self, cid: str):
        """Remove content with the given CID from this IPFS node's storage.
        Note: removes all unpinned content from this IPFS node's storage.
        Args:
            cid (str): the IPFS content ID (CID) of the resource to unpin
        """
        self.unpin(cid)
        self._http_client.repo.gc()

    def list_pins(
        self, cids_only: bool = False, cache_age_s: int | None = None
    ):
        """Get the CIDs of files we have pinned on IPFS
        Args:
            cids_only (bool): if True, returns a plain list of IPFS CIDs
                otherwise, returns a list of dicts of CIDs and their pinning type
            cache_age_s (int): getting the of pins from IPFS can take several
                seconds. IPFS_API therefore caches each result. If the age of the
                cache is less than this parameter, the cacheed result is returned,
                otherwise the slow process of getting the latest list of pins is
                used.
        Returns:
            list(): a list of the CIDs of pinned objects. The list element type
                depends on the cids_only parameter (see above)
        """
        if (
            self.__pins_cache
            and cache_age_s
            and (datetime.now(UTC) - self.__pins_cache["date"]).total_seconds()
            < cache_age_s
        ):
            data = self.__pins_cache["data"]
        else:
            data = self._http_client.pin.ls(timeout=500)["Keys"].as_json()
            self.__pins_cache = {"date": datetime.now(UTC), "data": data}
        if cids_only:
            return list(data.keys())
        else:
            return data

    def find_providers(self, cid):
        """Lookup/find out which IPFS nodes provide the file with the given CID
        (including onesself).
        E.g. to check if this computer hosts a file with a certain CID:
        def DoWeHaveFile(cid:str):
            ipfs_api.my_id() in ipfs_api.find_providers(cid)
        Args:
            cid (str): cid (str): the IPFS content ID (CID) of the resource to look up
        Returns:
            list: the peer IDs of the IPFS nodes who provide the file
        """
        responses = self._http_client.routing.findprovs(cid)
        peers = []
        for response in responses:
            if not isinstance(
                response, ipfshttpclient.client.base.ResponseBase
            ):
                continue
            if response["Type"] == 4:
                for resp in response["Responses"]:
                    if resp["ID"] and resp["ID"] not in peers:
                        peers.append(resp["ID"])
        return peers
