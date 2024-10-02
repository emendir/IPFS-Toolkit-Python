# IPFS-Toolkit Progressive ChangeLog 
This library is still under development and is currently being tested in various use-case projects. Due to its early stage of development, many successive versions of this library are not fully backward-compatible with their previous versions.

## v0.5.25 (2024-10-02)
- Performance improvements:
    - ipfs_api.pubsub: no longer uses temporary files, so `OSError Too many open files` errors are less common, increasing possible throughput
    - ipfs_peers.PeerMonitor: optimised data storage, so `OSError Too many open files` errors are less common, increasing possible throughput
## v0.5.24 (2024-08-22)
- `ipfs_datatransmission`: for various objects, don't throw errors on multiple callings of `.terminate()`

## v0.5.23 (2024-04-21)
- `ipfs_api.get_ipns_record_validity()`: added keword arguments

## v0.5.22 (2024-03-28)
- `ipfs_api.get_ipns_record_validity()`: new function
- `ipfs_http_client2.name.inspectlist()`: added missing IPFS RPC 'name/inspect' call
- `ipfs_http_client2.routing`: started adding missing IPFS RPC 'routing' section

## v0.5.20 (2024-03-17)
- ipfs_http_client2.swarm.filters.list(): added missing IPFS RPC 'swarm/filters' call

## v0.5.19 (2023-11-10)
- ipfs_api.remove(): new feature

## v0.5.18 (2023-11-10)
- ipfs_api.predict_cid(): new feature

## v0.5.17 (2023-10-23)
- ipfs_peers: new find_all_peers function to try to connect to all peers now

## v0.5.16 (2023-10-08)
- ipfs_peers: Bugfix for while loading peer from serial where last_seen is null 
- updated to systemd docker container for tests

## v0.5.15 (2023-9-20)
- ipfs_peers.PeerMonitor.terminate(): option to wait until termination is finished
- ipfs_api.PubsubListener.terminate(): option to wait until termination is finished

## v0.5.14 (2023-7-3)
- ipfs_peers.PeerMonitor: fixed CPU-loading bug in PeerMonitor

## v0.5.13 (2023-6-24)
- ipfs_peers.PeerMonitor: reduced congestion of access to ipfs_http_client

## v0.5.12 (2023-5-6)
- ipfs_peers.PeerMonitor: bugfixfor loading empty config file
- ipfshttpcient2: implementet p2p.ls()


## v0.5.11 (2023-5-6)
- ipfs_peers.PeerMonitor: bugfixes for rare cases in multi-threaded access

## v0.5.10 (2023-5-3)
- ipfs_api.pins: new function
- ipfs_peers.PeerMonitor: bugfix in save
## v0.5.9 (2023-5-2)
- is_peer_connected: new function
- ipfs_peers: I had forgotten to get this module installed by setuptools!
- ipfs_peers.PeerMonitor: cleanup old peers to prevent endless datastore growth
## v0.5.6 (2023-4-30)
- ipfs_peers: new module to extend the functionality of ipfs_lns. Docs coming soon.
- list_peer_multiaddrs renamed to list_peers to avoid confusion with get_peer_multiaddrs
- get_peer_multiaddrs: new function

## v0.5.5 (2023-04-29)
- ipfs_api: New (improved!) system for checking on the status of the IPFS daemon, allowing for cleaner code when waiting for IPFS daemon to start, starting it manually etc. See [Examples/Demo-Check-IPFS-Status.py](Examples/Demo-Check-IPFS-Status.py)
- ipfs_datatransmission: raise ConvListenTimeout **from None**
- ipfs_cli: fixed PubsubListener thread cleanup
- ipfs_cli: is_daemon_running renamed to is_ipfs_running

## v0.5.4 (2023-04-23)
- ipfs_datatransmission.Conversation.start(): bugfix in timeout

## v0.5.2 (2023-04-23)
This update is a patch to fix dependency version issues with httpx and httpcore modules.

## v0.5.1 (2023-03-22)
- ipfs_datatransmission.Conversation: termination of threads if the start() method returns an error.

## v0.5.0 (2023-03-12) (not backward-compatible)
### Renaming
With version 0.5.0, all functions class methods have been renamed from PascalCase to snake_case to comply with the standard PEP8 naming conventions. 
#### Parameter Renaming in Many Functions:
- `peerID` -> `peer_id`.
- `conv_name` -> `conv_name`
#### Other:
- In ipfs_datatransmission, many attributes of classes that shouldn't be used by API users have been made hidden by prepending "_" to their names.
- ipfs_datatransmission.ListenTimeout has been renamed to ConvListenTimeout
### Other API Changes:
- CatFile renamed to read_file
- ipfs_api: IPFS libp2p stream-mounting functions ( previously ForwardFromPortToPeer(), ListenOnPort(), ClosePortForwarding()):
  - Renamed and Reorganised to:
    - create_tcp_sending_connection()
    - create_tcp_listening_connection()
    - close_all_tcp_connections()
    - close_tcp_sending_connection()
    - close_tcp_listening_connection()
  -> with clearer parameters
- ipfs_datatransmission: FileTransmitter now starts transmitting file automatically
### Features:
- ipfs_api.pubsub_subscribe: now has a timeout option. Note that it never lasted forever even without the timeout :(
- ipfs_datatransmission.join_conversation: new function to simplify the previously needed two lines of code needed for joining conversations `conv = Conversation();conv.join(...)` into one `conv = join_conversation(...)`

### IPFS-DataTransmission Protocol Updates
With version 0.5.0, the basic communication protocol on which all of the features of the ipfs_datatransmission module are built has been improved to bring a massive increase in the speed of connection establishment. Unfortunately, this update lacks backward compatibility, which means that if you have built a project that uses ipfs_datatransmission, instances of your program running v0.4.X and v0.5.X of IPFS-Toolkit won't be able to communicate with each other.


## v0.4.4 (2023-01-28)
- ipfs_api.topic_peers(): new function to get the number of peers we are connected to on a pubsub topic

## v0.4.3 (2023-01-24)
bugfix

## v0.4.2 (2023-01-23)
- implemented security patch by TrellixVulnTeam CVE-2007-4559

## v0.4.1 (2023-01-23)
- IFPS_API: added download(cid, path) function which can download IPFS file and folders. The download_file(ID, path) function is now deprecated.

## v0.4.0 (2022-12-02)
- ipfs_datatransmission: All functions now throw exceptions on failure instead of quietly returning False
- ipfs_api: create_tcp_sending_connection now throws exceptions on failure instead of quietly returning False
- ipfs_datatransmission.Conversation.listen_for_file: two timeout parameters: abs_timeout, no_coms_timeout
- ipfs_datatransmission.Conversation.transmit_file: progress callback now supports 1-4 parameters
- ipfs_datatransmission.FileTransmissionReceiver: progress callback now supports 1-4 parameters

## v0.3.9 (2022-11-15)
ipfs_datatransmission: fixed thread termination bug in Conversation (up to this point not all threads belonging to Conversation would be stopped when calling Conversation.terminate(), leaving unused background threads open)

## v0.3.8
ipfs_api.find_providers(cid): newly added function which returns a list of peers who provide the file with the given CID (including onesself)

## v0.3.7
ipfs_datatransmission.start_conversation: added the `dir` parameter for file receptions

## v0.3.6
ipfs_datatransmission.Conversation: listen_for_file returns a dict of filepath and metadata instead of only filepath

## v0.3.5
ipfs_datatransmission: debugged Conversation.listen_for_file

## v0.3.2
ipfs_cli: added ipfs_cli as a fallback API to IPFS in case the ipfshttpcient2 API fails to load.

## v0.3.1
ipfs_api: create_tcp_sending_connection now returns a boolean indicating whether or not it successfully connected to the specified port.
## v0.3.0
ipfs_api: PubSub (ipfs_api.publish_to_topic & ipfs_api.subscribe_to_topic) is now compatible with IPFS v0.11.0! As described in the [IPFS changelog](https://github.com/ipfs/go-ipfs/releases/tag/v0.11.0), the official PubSub's publish function now accepts files instead of plain data. ipfs_api.publish_to_topic however accepts plain (as strings or bytearrays) as well as filepaths, saving the data to temporary files to publish so that the user doesn't have to bother with it. Also new is that (when using IPFS >= v0.11.0) SubscribToTopic passes a dictionary that includes the message data (as bytes) as well as its sender as the parameter to its eventhandler, instead of just the message data as a string.
When using a version of IPFS below v0.11.0, the behaviour of the (ipfs_api.publish_to_topic & ipfs_api.subscribe_to_topic) remains as it was in the older versions of IPFS-Toolkit (v0.2.X).

## v0.2.11
ipfs_api: Bugfix in update_ipns_record
## v0.2.10:
IPFS_FileTransmission: add _.PART_ file extension to files currently being received

## v0.2.7:
ipfs_datatransmission: listen_to_buffers: added eventhandlers_on_new_threads parameter to improve efficiency if needed

## v0.2.6:
ipfs_datatransmission: got BufferSender and listen_to_buffers working again
Examples: corrected docstrings

## v0.2.5:
ipfshttpclient2: bugfix correcting unintended IDE import rearrangement
ipfs_datatransmission: made encryption & decryption callbacks private attributes 

## v0.2.4:
ipfs_api:
  - subscribe_to_topic(): Returns a listener object (PubsubListener), on which terminate() and listen() functions can be called to stop and restart the PubSub Subscription.
ipfs_datatransmission:
  - Conversations and FileTransission: Encryption support is now integrated! Encryption and decryption callbacks can be passed as optional parameters when starting, joining, or listening for conversations and file transmissions.
## v0.2.3 (not backward-compatible):
ipfs_datatransmission:
  - Data transmission protocol (in transmit_data() and listen_for_transmissions()) changed from using the faster ZMQ protocol to simple TCP sockets.  
  Reasons:
    - ZMQ is not supported by all python virtual environments
    - using ZMQ over Libp2pStreamMounting transports sometimes failed without warning. Superior reliability of the current TCP system is supposed, but not yet definitvely studied.
  - Conversation.SendFiles: Conversation objects now have functions to send and receive files, receiving files with callback functions and/or thread-blocking waiting functions.

## v0.2.2 (not backward-compatible):
Highlights:
  - ipfs_datatransmission:
    - failure handling system
    - implemented ZMQ in data transmission (replaced with TCP in v0.2.3)
    - Conversation.listen
    - FileTransission progress callbacks