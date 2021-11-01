This is a Python module that enables two users to easily transmit data of any length to each other over the IPFS Network.
See Prerequisites.txt for instructions on how to install all the software tools needed to use it.

This module has 3 pairs functions for use by the user:
- Simple data transmission:
    - TransmitData(data, peerID, listener_name)
    - ListenForTransmissions(listener_name, eventhandler)
- File Transmission:
    - TransmitFile(data, peerID, listener_name)
    - ListenForFileTransmissions(listener_name, eventhandler)
- Ping-Pong data Transmission:
    - StartConversation(data, peerID, listener_name)
    - ListenForConversations(listener_name, eventhandler)

##Listener Functions:
The listener functions (ListenForTransmissions, ListenForFileTransmissions and ListenForConversations) produce Listener objects () that run on their own threads waiting for incoming data transmission or conversation requests. When another computer wants to send the first computer somthing, the other computer sends a transmission request which the Listener object receives and reacts to by creating a Transmission reception object () which runs on its own separate thread to receive the transmission, or in the case of the conversation listener, calls its user-defined eventhandler so that the conversation can be joined or ignored.
This system of receiving data transmissions / conversations allows a computer to receive multiple transmission addressed to the same listener simultaneously.
Multiple Listeners of the same type (the types being DataTransmission, FileTransmission, or Conversation) can be run simultaneously and independently, for example by different programs. Those different listeners (instances of ListenForTransmissions) must me named to distinguish them from each other for addressing purposes. This name is the "listener_name" parameter in the listener functions. The name is chosen by the user when creating the listener (e.g. when calling ListenForTransmission()), and must be provided when starting a transmission (e.g. when calling TransmitData()).



##IPFS Technicalities:
How does IPFS-DataTransmission use IPFS to to send data to another computer? After all, IPFS is a file system and made for sharing and storing files, creating a content addressed internet. Does it really provide the functionality for two computers to communicate directly which each other?
Yes, IPFS does provide that functionality, although as of November 2021 that is still an experimental feature. That's why you have to configure IPFS to enable that feature as described in Prerequisites.txt.
After all, IPFS relies on peers sending data to each other over its decentralised network using a communication technology called libp2p. IPFS-DataTransmission essentially uses the libp2p module inside of the IPFS process running on the computer to communicate to other computers via an access point to the module which IPFS provides, the experimental feature which IPFS calls Libp2pStreamMounting. Libp2pStreamMounting works by allowing the user to set up a port forwarding system on the computer between the user's program (in this case IPFS-DataTransmission) and the libp2p process inside of IPFS. After setting up this port forwarding the user (in this case the IPFS-DataTransmission script) can communicate to the chosen local port on their computer, and IPFS forwards that communication to the libp2p module runnning inside of IPFS on the other computer, which forwards it in turn to a preconfigured port on that computer, to be listened to by the user (in this case an IPFS-DataTransmission Listener object).
Because the python API for interacting with IPFS (ipfshttpclient) doesn't yet support this experimental feature, I have updated the module myself, the result of which is the ipfshttpclient2 folder in this code project, which will remain part of this project until the changes are integrated into the official ipfshttpclient module.
