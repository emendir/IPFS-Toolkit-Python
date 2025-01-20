from base64 import urlsafe_b64encode
from .. import utils
from .. import multipart

import typing as ty

from . import base


class SubChannel:
    """Wrapper for a pubsub subscription object that allows for easy
    closing of subscriptions.
    """

    def __init__(self, sub):
        self.__sub = sub  # type: str

    def read_message(self):
        return next(self.__sub)

    def __iter__(self):
        return self.__sub

    def close(self):
        self.__sub.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class Section(base.SectionBase):
    @base.returns_single_item(base.ResponseBase)
    def ls(self, **kwargs: base.CommonArgs):
        """Lists subscribed topics by name

        This method returns data that contains a list of
        all topics the user is subscribed to. In order
        to subscribe to a topic ``pubsub.sub`` must be called.

        .. code-block:: python

                # subscribe to a channel
                >>> with client.pubsub.sub("hello") as sub:
                ...     client.pubsub.ls()
                {
                        'Strings' : ["hello"]
                }

        Returns
        -------
                dict

        +---------+-------------------------------------------------+
        | Strings | List of topic the IPFS daemon is subscribbed to |
        +---------+-------------------------------------------------+
        """
        return self._client.request('/pubsub/ls', decoder='json', **kwargs)

    @base.returns_single_item(base.ResponseBase)
    def peers(self, topic: ty.Optional[str] = None, **kwargs: base.CommonArgs):
        """Lists the peers we are pubsubbing with

        Lists the IDs of other IPFS users who we
        are connected to via some topic. Without specifying
        a topic, IPFS peers from all subscribed topics
        will be returned in the data. If a topic is specified
        only the IPFS id's of the peers from the specified
        topic will be returned in the data.

        .. code-block:: python

                >>> client.pubsub.peers()
                {'Strings':
                                [
                                        'QmPbZ3SDgmTNEB1gNSE9DEf4xT8eag3AFn5uo7X39TbZM8',
                                        'QmQKiXYzoFpiGZ93DaFBFDMDWDJCRjXDARu4wne2PRtSgA',
                                        ...
                                        'QmepgFW7BHEtU4pZJdxaNiv75mKLLRQnPi1KaaXmQN4V1a'
                                ]
                }

                ## with a topic

                # subscribe to a channel
                >>> with client.pubsub.sub('hello') as sub:
                ...     client.pubsub.peers(topic='hello')
                {'String':
                                [
                                        'QmPbZ3SDgmTNEB1gNSE9DEf4xT8eag3AFn5uo7X39TbZM8',
                                        ...
                                        # other peers connected to the same channel
                                ]
                }

        Parameters
        ----------
        topic
                The topic to list connected peers of
                (defaults to None which lists peers for all topics)

        Returns
        -------
                dict

        +---------+-------------------------------------------------+
        | Strings | List of PeerIDs of peers we are pubsubbing with |
        +---------+-------------------------------------------------+
        """
        args = (topic,) if topic is not None else ()
        return self._client.request('/pubsub/peers', args, decoder='json', **kwargs)

    @base.returns_no_item
    def publish(self, topic: str, data_file: utils.clean_file_t,
                **kwargs: base.CommonArgs):
        """Creates a new merkledag object based on an existing one

        The new object will have the same links as the previous object, but with
        the provided data appended to it.


        Parameters
        ----------
        cid
                The hash of an ipfs object to modify
        new_data
                The data to append to the object's data section

        Returns
        -------
                dict

        +------+----------------------------------+
        | Hash | Hash of the newly derived object |
        +------+----------------------------------+
        """
        args = (EncodeBase64Url(topic),)
        body, headers = multipart.stream_files(data_file, chunk_size=self.chunk_size)

        return self._client.request('/pubsub/pub', args, decoder='json',
                                    data=body, headers=headers, **kwargs)

    @base.returns_no_item
    def publish_old(self, topic: str, payload: str, **kwargs: base.CommonArgs):
        """publish a message to a given pubsub topic
        This function is the old version of publish which has been broken since IPFS v0.11.0.
        It has been replaced by 

        Publishing will publish the given payload (string) to
        everyone currently subscribed to the given topic.

        All data (including the ID of the publisher) is automatically
        base64 encoded when published.

        .. code-block:: python

                # publishes the message 'message' to the topic 'hello'
                >>> client.pubsub.publish('hello', 'message')
                []

        Parameters
        ----------
        topic
                Topic to publish to
        payload
                Data to be published to the given topic

        Returns
        -------
                list
                        An empty list
        """
        args = (topic, payload)
        return self._client.request('/pubsub/pub', args, decoder='json', **kwargs)

    def subscribe(self, topic: str, discover: bool = False, timeout=None, **kwargs: base.CommonArgs):
        """Subscribes to mesages on a given topic

        Subscribing to a topic in IPFS means anytime
        a message is published to a topic, the subscribers
        will be notified of the publication.

        The connection with the pubsub topic is opened and read.
        The Subscription returned should be used inside a context
        manager to ensure that it is closed properly and not left
        hanging.

        .. code-block:: python

                >>> sub = client.pubsub.subscribe('testing')
                >>> with client.pubsub.subscribe('testing') as sub:
                ... 	# publish a message 'hello' to the topic 'testing'
                ... 	client.pubsub.publish('testing', 'hello')
                ... 	for message in sub:
                ... 		print(message)
                ... 		# Stop reading the subscription after
                ... 		# we receive one publication
                ... 		break
                {'from': '<base64encoded IPFS id>',
                 'data': 'aGVsbG8=',
                 'topicIDs': ['testing']}

                # NOTE: in order to receive published data
                # you must already be subscribed to the topic at publication
                # time.

        Parameters
        ----------
        topic
                Name of a topic to subscribe to

        discover
                Try to discover other peers subscibed to the same topic
                (defaults to False)

        Returns
        -------
                :class:`SubChannel`
                        Generator wrapped in a context manager that maintains a
                        connection stream to the given topic.
        """
        args = (EncodeBase64Url(topic),)
        return SubChannel(self._client.request('/pubsub/sub', args, stream=True, decoder='json', timeout=timeout))

    def subscribe_old(self, topic: str, discover: bool = False, **kwargs: base.CommonArgs):
        """Subscribes to mesages on a given topic

        Subscribing to a topic in IPFS means anytime
        a message is published to a topic, the subscribers
        will be notified of the publication.

        The connection with the pubsub topic is opened and read.
        The Subscription returned should be used inside a context
        manager to ensure that it is closed properly and not left
        hanging.

        .. code-block:: python

                >>> sub = client.pubsub.subscribe('testing')
                >>> with client.pubsub.subscribe('testing') as sub:
                ... 	# publish a message 'hello' to the topic 'testing'
                ... 	client.pubsub.publish('testing', 'hello')
                ... 	for message in sub:
                ... 		print(message)
                ... 		# Stop reading the subscription after
                ... 		# we receive one publication
                ... 		break
                {'from': '<base64encoded IPFS id>',
                 'data': 'aGVsbG8=',
                 'topicIDs': ['testing']}

                # NOTE: in order to receive published data
                # you must already be subscribed to the topic at publication
                # time.

        Parameters
        ----------
        topic
                Name of a topic to subscribe to

        discover
                Try to discover other peers subscibed to the same topic
                (defaults to False)

        Returns
        -------
                :class:`SubChannel`
                        Generator wrapped in a context manager that maintains a
                        connection stream to the given topic.
        """
        args = (topic, discover)
        return SubChannel(self._client.request('/pubsub/sub', args, stream=True, decoder='json', timeout=timeout))


def EncodeBase64Url(data: str):
    """PLerforms the URL-Safe multibase encoding required by the new pubsub function (since IFPS v0.11.0) on strings"""
    return "u" + urlsafe_b64encode(data.encode()).rstrip(b'=').decode()
