A library for working with IPFS in Python.  
It includes a programmer-friendly wrapper called __IPFS-API__ for the official IPFS Python API (ipfshttpclient), a module called __IPFS-DataTransmission__ for direct P2P data transmission between two IPFS-Nodes and a module called __IPFS-LNS__ for remembering the multiaddrs of known IPFS nodes ("contacts") to speed up connection times.

# Package Contents:
## Modules:
- __IPFS_API__: a wrapper for the module ipfshttpclient2 that makes it easier to work with IPFS in Python
- __IPFS_DataTransmission__: a Python module that enables P2P data transmission between IPFS nodes
- __IPFS_LNS__: a Python module that allows IPFS nodes and their multiaddresses to be stored in app data to make them easier to find in the IP layer of the internet (easier to connect to)
- __ipfshttpclient2__: a modified version of the official ipfshttpclient module that has been expanded to include the ipfs.p2p functions
## Other:
- __Examples__: a folder of scripts demonstrating how to work with IPFS_DataTransmission


# Getting started with IPFS-Toolkit:
1. Install IPFS-Toolkit (see below)
2. Read this _Modules Contained in IPFS-Toolkit_ section below to learn what this package contains and how it works. 
3. For IPFS-DataTransmission: Read and try out the demo scripts in the Examples folder.

## Setup
### Installation
`pip install IPFS-Toolkit`



### Prerequsites
IPFS-Toolkit is made for interacting with IPFS in the Python programming language. One configuration must be applied to IPFS in order to use IPFS-Toolkit's main features.
- __Install IPFS__ (Desktop version or CLI, doesn't matter).
    https://docs.ipfs.io/install/
- __Enable "Libp2pStreamMounting" in IPFS:__  
  __Desktop Version/WebUI:__ on the Settings tab, scroll down to "IPFS CONFIG" and change the line that reads:
      change from:
      "Libp2pStreamMounting": false,
      to:
      "Libp2pStreamMounting": true,
  Click the "Save" button and restart IPFS.

  __CLI Version:__ run:  
    `ipfs config --json Experimental.Libp2pStreamMounting true`
- __Python3__, version 3.6 or above
    https://www.python.org/downloads/
- __Pip__ for Python3:
    https://pip.pypa.io/en/stable/installing/
- If you want to use the source code, install the following prerequisite Python modules:  
    `pip3 install setuptools`  
    `pip3 install wheel`  
    `pip3 install multiaddr`  
    `pip3 install appdirs`  
    `pip3 install multiaddr`  
    `pip3 install appdirs`  
    `pip3 install idna`  
    `pip3 install httpcore`  
    `pip3 install httpx`

# Modules Contained in IPFS-Toolkit
## IPFS-API
`import IPFS_API`

Usage examples:  
`print(IPFS_API.MyID()) # print your IPFS peer ID`  
`cid = IPFS_API.Upload('./SomeFileOrDir') # upload file or directory to IPFS and store it's CID in a variable`  

`# Managing IPNS keys`  
`IPFS_API.CreateIPNS_Record('MyWebsite') # generate a pair of IPNS name keys`  
`IPFS_API.UpdateIPNS_Record('MyWebsite', './SomeFileOrDir') # upload file to IPFS & publish `  
`IPFS_API.UpdateIPNS_RecordFromHash('MyWebsite', cid) # publish IPFS content to IPNS key`  

`# IPFS PubSub`  
`IPFS_API.SubscribeToTopic("test", print) # print is the eventhandler`  
`IPFS_API.PublishToTopic("test", "Hello there!")`


## IPFS-Datatransmission
`import IPFS_DataTransmission`

A Python module for limitless, easy, private peer-to-peer data transmission other over the IPFS Network.

This module has 3 pairs functions for use by the user:
- __Simple data transmission:__
    - `TransmitData(data, peerID, listener_name)`
    - `ListenForTransmissions(listener_name,` eventhandler)
- __File Transmission:__
    - `TransmitFile(data, peerID, listener_name)`
    - `ListenForFileTransmissions(listener_name, eventhandler)`
- __Conversations (Ping-Pong data Transmission):__
    - `StartConversation(data, peerID, listener_name)`
    - `ListenForConversations(listener_name, eventhandler)`

### Listener Functions:
The listener functions (ListenForTransmissions, ListenForFileTransmissions and ListenForConversations) produce Listener objects () that run on their own threads waiting for incoming data transmission or conversation requests. When another computer wants to send the first computer somthing, the other computer sends a transmission request which the Listener object receives and reacts to by creating a Transmission reception object () which runs on its own separate thread to receive the transmission, or in the case of the conversation listener, calls its user-defined eventhandler so that the conversation can be joined or ignored.
This system of receiving data transmissions/conversations allows a computer to receive multiple transmission addressed to the same listener simultaneously.
Multiple Listeners of the same type (the types being DataTransmission, FileTransmission, or Conversation) can be run simultaneously and independently, for example by different programs. Those different listeners (instances of ListenForTransmissions) must me named to distinguish them from each other for addressing purposes. This name is the "listener_name" parameter in the listener functions. The name is chosen by the user when creating the listener (e.g. when calling ListenForTransmission()), and must be provided when starting a transmission (e.g. when calling TransmitData()).

## IPFS-LNS:
`import IPFS_LNS`

IPFS-LNS (IPFS Local Name System) allows you to store IPFS nodes' peer IDs and names in a database stored on your local machine. IPFS-LNS also stores a list of multiaddresses (essentially IP addresses) that the peer has been known to use, as long as you use IPFS-LNS to connect or check the connection to that peer. Every time you try to connect to the peer, IPFS-LNS tries to specifically connect to the peer using the known multiaddresses from previous connections, which can dramatically increase the speed of doing so compared to searching the whole IPFS network for the peer.


Basic usage:  
`import IPFS_API`  

`# check connection to peer of peerID "QmHash" and whom we call "Bob", add him to our list of known peers ("contacts") if he is not already added`  
`IPFS_API.CheckPeerConnection("QmHash", "Bob") `

`import IPFS_LNS`
`peerID = IPFS_LNS.LookUpContact("Bob") # get the contact 'Bob's IPFS peer ID`

# IPFS Technicalities:
How does IPFS-DataTransmission use IPFS to to send data to another computer? After all, IPFS is a file system and made for sharing and storing files, creating a content addressed internet. Does it really provide the functionality for two computers to communicate directly which each other?  
Yes, IPFS does provide that functionality, although as of November 2021 that is still an experimental feature. That's why you have to configure IPFS to enable that feature as described in Prerequisites.txt.  
After all, IPFS relies on peers sending data to each other over its decentralised network using a communication technology called libp2p. IPFS-DataTransmission essentially uses the libp2p module inside of the IPFS process running on the computer to communicate to other computers via an access point to the module which IPFS provides, the experimental feature which IPFS calls Libp2pStreamMounting. Libp2pStreamMounting works by allowing the user to set up a port forwarding system on the computer between the user's program (in this case IPFS-DataTransmission) and the libp2p process inside of IPFS. After setting up this port forwarding the user (in this case the IPFS-DataTransmission script) can communicate to the chosen local port on their computer, and IPFS forwards that communication to the libp2p module runnning inside of IPFS on the other computer, which forwards it in turn to a preconfigured port on that computer, to be listened to by the user (in this case an IPFS-DataTransmission Listener object).  
Because the Python API for interacting with IPFS (ipfshttpclient) doesn't yet support this experimental feature, I have updated the module myself, the result of which is the ipfshttpclient2 folder in this code project, which will remain part of this project until the changes are integrated into the official ipfshttpclient module.

# Links
Naturally, I host this project on IPFS too
### Source Code:
IPFS (faster):
https://ipfs.io/ipfs/QmdCszoMQii7oVKHe6xmHpd8eHyRC8n4LpQu4ii7nLzu7L  
IPNS (more likely to be up-to-date):
https://ipfs.io/ipns/k2k4r8k7h909zdodsvbxe32sahpfdkqcqqn1npblummw4df6iv7dj5xh
### Website:
IPFS (faster):
https://ipfs.io/ipfs/QmQRUfBXnjqDkGKVUNro3BCUF7frcpkQ1NnRq6zaUfva8u  
IPNS (more likely to be up-to-date):
https://ipfs.io/ipns/k2k4r8m2dzqi5s8jm3shm77sr1728ex7bsds0fk6e9gkf2ld2f3mnhcy
