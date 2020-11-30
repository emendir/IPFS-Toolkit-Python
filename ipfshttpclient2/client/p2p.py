import typing as ty

from . import base




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
	def forward(self, protocol: str, peer_id: str, port: str, **kwargs: base.CommonArgs):
		"""Forward connections to libp2p service

		Forward connections made to <listen-address> to <target-address>.

		.. code-block:: python

			# forwards connections made to 'port' to 'QmHash'
			>>> client.p2p.forward('protocol', 'port', 'QmHash')
			[]

		Parameters
		----------
		protocol
			specifies the libp2p protocol name to use for libp2p connections and/or handlers. It must be prefixed with '/x/'.
		port
			Listening endpoint
        PeerID
			Target endpoint

		Returns
		-------
			list
				An empty list
		"""
		args = (protocol, peer_id, port)
		return self._client.request('/p2p/forward', args, decoder='json', **kwargs)

	@base.returns_no_item
	def listen(self, protocol: str, port: str, **kwargs: base.CommonArgs):
		"""Create libp2p service


		.. code-block:: python

			Create libp2p service and forward IPFS connections to 'port'
			>>> client.p2p.listen('protocol', 'port')
			[]

		Parameters
		----------
		protocol
			specifies the libp2p handler name. It must be prefixed with '/x/'.
		port
			Listener port to which to forward incoming connections


		Returns
		-------
			list
				An empty list
		"""
		args = (protocol, port)
		return self._client.request('/p2p/listen', args, decoder='json', **kwargs)

	#@base.returns_single_item(base.ResponseBase)
	def close(self, all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None, **kwargs: base.CommonArgs):
		"""Create libp2p service


		.. code-block:: python

			Create libp2p service and forward IPFS connections to 'port'
			>>> client.p2p.listen('protocol', 'port')
			[]

		Parameters
		----------
		protocol
			specifies the libp2p handler name. It must be prefixed with '/x/'.
		port
			Listener port to which to forward incoming connections


		Returns
		-------
			list
				An empty list
		"""
		opts = {"all": all, "protocol": protocol, "listen-address": listenaddress, "target-address": targetaddress}
		if all is not None:
			opts["all"] = all
		if protocol is not None:
			opts["protocol"] = str(protocol)
		if listenaddress is not None:
			opts["listen-address"] = str(listenaddress)
		if targetaddress is not None:
			opts["target-address"] = str(targetaddress)

		kwargs.setdefault("opts", {}).update(opts)
		args = (all,) #if all is not None else ()
		return self._client.request('/p2p/close', decoder='json', **kwargs)
