# IPFS-Toolkit Progressive ChangeLog 
This library is still under development and is currently being tested in various use-case projects. Due to its early stage of development, many successive versions of this library are not fully backward-compatible with their previous versions.

## v0.2.5:
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