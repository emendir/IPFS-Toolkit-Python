# IPFS-Toolkit Progressive ChangeLog 
This library is still under development and is currently being tested in various use-case projects. Due to its early stage of development, many successive versions of this library are not fully backward-compatible with their previous versions.

## v0.4.0
- IPFS_DataTransmission: All functions now throw exceptions on failure instead of quietly returning False
- IPFS_API: ForwardFromPortToPeer now throws exceptions on failure instead of quietly returning False
- IPFS_DataTransmission.Converstion.ListenForFile: two timeout parameters: abs_timeout, no_coms_timeout
- IPFS_DataTransmission.FileTransmissionReceiver: progress handler now also supports 1-4 parameters

## v0.3.9 (2022-11-15)
IPFS_DataTransmission: fixed thread termination bug in Conversation (up to this point not all threads belonging to Conversation would be stopped when calling Conversation.Terminate(), leaving unused background threads open)

## v0.3.8
IPFS_API.FindProviders(cid): newly added function which returns a list of peers who provide the file with the given CID (including onesself)

## v0.3.7
IPFS_DataTransmission.StartConversation: added the `dir` parameter for file receptions

## v0.3.6
IPFS_DataTransmission.Conversation: ListenForFile returns a dict of filepath and metadata instead of only filepath

## v0.3.5
IPFS_DataTransmission: debugged Conversation.ListenForFile

## v0.3.2
IPFS_CLI: added IPFS_CLI as a fallback API to IPFS in case the ipfshttpcient2 API fails to load.

## v0.3.1
IPFS_API: ForwardFromPortToPeer now returns a boolean indicating whether or not it successfully connected to the specified port.
## v0.3.0
IPFS_API: PubSub (IPFS_API.PublishToTopic & IPFS_API.SubscribeToTopic) is now compatible with IPFS v0.11.0! As described in the [IPFS changelog](https://github.com/ipfs/go-ipfs/releases/tag/v0.11.0), the official PubSub's publish function now accepts files instead of plain data. IPFS_API.PublishToTopic however accepts plain (as strings or bytearrays) as well as filepaths, saving the data to temporary files to publish so that the user doesn't have to bother with it. Also new is that (when using IPFS >= v0.11.0) SubscribToTopic passes a dictionary that includes the message data (as bytes) as well as its sender as the parameter to its eventhandler, instead of just the message data as a string.
When using a version of IPFS below v0.11.0, the behaviour of the (IPFS_API.PublishToTopic & IPFS_API.SubscribeToTopic) remains as it was in the older versions of IPFS-Toolkit (v0.2.X).

## v0.2.11
IPFS_API: Bugfix in UpdateIPNS_Record
## v0.2.10:
IPFS_FileTransmission: add _.PART_ file extension to files currently being received

## v0.2.7:
IPFS_DataTransmission: ListenToBuffers: added eventhandlers_on_new_threads parameter to improve efficiency if needed

## v0.2.6:
IPFS_DataTransmission: got BufferSender and ListenToBuffers working again
Examples: corrected docstrings

## v0.2.5:
ipfshttpclient2: bugfix correcting unintended IDE import rearrangement
IPFS_DataTransmission: made encryption & decryption callbacks private attributes 

## v0.2.4:
IPFS_API:
  - SubscribeToTopic(): Returns a listener object (PubsubListener), on which Terminate() and Listen() functions can be called to stop and restart the PubSub Subscription.
IPFS_DataTransmission:
  - Conversations and FileTransission: Encryption support is now integrated! Encryption and decryption callbacks can be passed as optional parameters when starting, joining, or listening for conversations and file transmissions.
## v0.2.3 (not backward-compatible):
IPFS_DataTransmission:
  - Data transmission protocol (in TransmitData() and ListenForTransmissions()) changed from using the faster ZMQ protocol to simple TCP sockets.  
  Reasons:
    - ZMQ is not supported by all python virtual environments
    - using ZMQ over Libp2pStreamMounting transports sometimes failed without warning. Superior reliability of the current TCP system is supposed, but not yet definitvely studied.
  - Conversation.SendFiles: Conversation objects now have functions to send and receive files, receiving files with callback functions and/or thread-blocking waiting functions.

## v0.2.2 (not backward-compatible):
Highlights (see [ChangeLog-v0.2.2](./ChangeLog-v0.2.2.md) for details):
  - IPFS_DataTransmission:
    - failure handling system
    - implemented ZMQ in data transmission (replaced with TCP in v0.2.3)
    - Conversation.Listen
    - FileTransission progress callbacks