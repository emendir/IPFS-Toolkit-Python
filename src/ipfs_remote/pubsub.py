import os
from ipfs_tk_generics.client import IpfsClient
from ipfs_tk_generics.pubsub import  BasePubSub, BasePubsubListener

from io import BytesIO
from threading import Thread
import os.path
import os
# import sys
# import subprocess
# import threading
# import multiprocessing
import base64
from base64 import urlsafe_b64decode, urlsafe_b64encode


class RemotePubSub(BasePubSub):
    def __init__(self, node: IpfsClient):
        self._node = node
        self._http_client = self._node._http_client

    def publish(self, topic, data):
        """Publishes te specified data to the specified IPFS-PubSub topic.
        Args:
            topic (str): the name of the IPFS PubSub topic to publish to
            data (str/bytearray): either the filepath of a file whose
                content should be published to the pubsub topic,
                or the raw data to be published as a string or bytearray.
                When using an older version of IPFS < v0.11.0 however,
                only plain data as a string is accepted.
        """
        if int(self._http_client.version()["Version"].split(".")[1]) < 11:
            return self._http_client.pubsub.publish_old(topic, data)

        if isinstance(data, str) and not os.path.exists(data):
            data = data.encode()
        if isinstance(data, bytes) or isinstance(data, bytearray):
            # Use an in-memory BytesIO object instead of a temporary file
            with BytesIO(data) as data_stream:
                # Call _publish with the BytesIO object
                self._http_client.pubsub.publish(topic, data_stream)
        else:
            self._http_client.pubsub.publish(topic, data)

    def subscribe(self, topic, eventhandler):
        """
        Listens to the specified IPFS PubSub topic, calling the eventhandler
        whenever a message is received, passing the message data and its sender
        to the eventhandler.
        Args:
            topic (str): the name of the IPFS PubSub topic to publish to
            eventhandler (function): the function to be executed whenever a message is received.
                                The eventhandler parameter is a dict with the keys 'data' and 'senderID',
                                except when using an older version of IPFS < v0.11.0,
                                in which case only the message is passed as a string.
        Returns:
            PubsubListener: listener object which can  be terminated with the .terminate() method (and restarted with the .listen() method)
        """
        return PubsubListener(self._node, topic, eventhandler)

    def list_peers(self, topic: str):
        """Looks up what IPFS nodes we are connected to who are listening on the given topic.
        Returns:
            list: peers we are connected to on the specified pubsub topic
        """
        return self._http_client.pubsub.peers(topic=_encode_base64_url(topic.encode()))["Strings"]


class PubsubListener(BasePubsubListener):
    """Listener object for PubSub subscriptions."""
    _terminate = False
    __listening = False
    sub = None
    _REFRESH_RATE = 5  # seconds. How often the pubsub HTTP listener ist restarted, also the maximum duration termination can take

    def __init__(self, node, topic, eventhandler):
        self._node = node
        self._http_client = node._http_client
        self.topic = topic
        self.eventhandler = eventhandler
        self.listen()

    def _listen(self):
        if self.__listening:
            return
        self.__listening = True
        """blocks the calling thread"""
        while not self._terminate:
            try:
                if int(self._http_client.version()["Version"].split(".")[1]) >= 11:
                    with self._http_client.pubsub.subscribe(self.topic, timeout=self._REFRESH_RATE) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = {
                                "senderID": message["from"],
                                "data": _decode_base64_url(message["data"]),
                            }

                            Thread(
                                target=self.eventhandler,
                                args=(data,),
                                name="ipfs_api.PubsubListener-eventhandler"
                            ).start()
                else:
                    with self._http_client.pubsub.subscribe_old(self.topic) as self.sub:
                        for message in self.sub:
                            if self._terminate:
                                self.__listening = False
                                return
                            data = str(base64.b64decode(
                                str(message).split('\'')[7]), "utf-8")
                            Thread(
                                target=self.eventhandler,
                                args=(data,),
                                name="ipfs_api.PubsubListener-eventhandler"
                            ).start()
            except:
                pass
                # print(f"IPFS API Pubsub: restarting sub {self.topic}")
        self.__listening = False

    def listen(self):
        self._terminate = False
        self.listener_thread = Thread(
            target=self._listen, args=(), name="ipfs_api.PubsubListener")
        self.listener_thread.start()

    def terminate(self, wait=False):
        """Stop this PubSub subscription, stop listening for data.
        May let one more pubsub message through
        Takes up to self._REFRESH_RATE seconds to complete.

        Args:
            wait (bool): whether or not this function should block until all
                activity has been stopped and resources have been cleaned up

        """
        self._terminate = True
        if self.sub:
            self.sub.close()
        if wait:
            self.listener_thread.join()


def _decode_base64_url(data: str):
    """Performs the URL-Safe multibase decoding required by some functions (since IFPS v0.11.0) on strings"""
    if isinstance(data, bytes):
        data = data.decode()
    _data = str(data)[1:].encode()
    missing_padding = len(_data) % 4
    if missing_padding:
        _data += b'=' * (4 - missing_padding)
    return urlsafe_b64decode(_data)


def _encode_base64_url(data: bytearray | bytes):
    """Performs the URL-Safe multibase encoding required by some functions (since IFPS v0.11.0) on strings"""
    if isinstance(data, str):
        data = data.encode()
    data = urlsafe_b64encode(data)
    while data[-1] == 61 and data[-1]:
        data = data[:-1]
    data = b'u' + data
    return data
