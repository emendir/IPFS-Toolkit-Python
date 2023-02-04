A library for working with IPFS in Python.  
It includes a programmer-friendly wrapper called __IPFS-API__ for the official IPFS Python API (ipfshttpclient), a module called __IPFS-DataTransmission__ for direct P2P data transmission between two IPFS-Nodes and a module called __IPFS-LNS__ for remembering the multiaddrs of known IPFS nodes ("contacts") to speed up connection times.

# Package Contents:
## Modules:
- __IPFS_API__: a wrapper for the module ipfshttpclient2 that makes it easier to work with IPFS in Python
- __IPFS_DataTransmission__: a Python module that enables P2P data transmission between IPFS nodes
- __IPFS_LNS__: a Python module that allows IPFS nodes and their multiaddresses to be stored in app data to make them easier to find in the IP layer of the internet (easier to connect to)
- __ipfshttpclient2__: a modified version of the official ipfshttpclient module that has been expanded to include the ipfs.p2p functions

## Other:
- __Examples__: a folder of scripts demonstrating how to work with ipfs_datatransmission


# Getting started with IPFS-Toolkit:
1. Install IPFS-Toolkit (see below)
2. Read the _Modules Contained in IPFS-Toolkit_ section below to learn what this package contains and how it works. 
3. For IPFS-DataTransmission: Read and try out the demo scripts in the Examples folder.

## setup
### Installation
`pip install IPFS-Toolkit`



### Prerequsites
IPFS-Toolkit is made for interacting with IPFS in the Python programming language. One configuration must be applied to IPFS in order to use IPFS-Toolkit's main features.
- __Install IPFS__ (Desktop version or CLI, doesn't matter).
    https://docs.ipfs.io/install/
- __Enable "Libp2pStreamMounting" in IPFS:__  
  __Desktop Version/WebUI:__ on the Settings tab, scroll down to "IPFS CONFIG" and change the line that reads:  
    change from:  
    `"Libp2pStreamMounting": false,`  
    to:  
    `"Libp2pStreamMounting": true,`  
  Click the "Save" button and restart IPFS.

  __CLI Version:__ run:  
    `ipfs config --json Experimental.Libp2pStreamMounting true`
- __Python3__, version 3.6 or above
    https://www.python.org/downloads/
- __Pip__ for Python3:
    https://pip.pypa.io/en/stable/installing/
- If you want to use the source code, install the following prerequisite Python modules:  
  (depending on your python installation you may need to use `pip` instead of `pip3` in the following commands)  
```bash
pip3 install setuptools  
pip3 install wheel  
pip3 install multiaddr  
pip3 install appdirs  
pip3 install multiaddr  
pip3 install appdirs  
pip3 install idna  
pip3 install httpcore  
pip3 install httpx
pip3 install zmq
```

# Modules Contained in IPFS-Toolkit
## IPFS-API
`import ipfs_api`

This has a simplified and more user-friendly yet limited API for interacting with IPFS compared to the ipfshttpclient.

Usage examples:  
```python
print(ipfs_api.my_id()) # print your IPFS peer ID  
cid = ipfs_api.publish('./SomeFileOrDir') # upload file or directory to IPFS and store it's CID in a variable  

# Managing IPNS keys  
ipfs_api.create_ipns_record('MyWebsite') # generate a pair of IPNS name keys  
ipfs_api.update_ipns_record('MyWebsite', './SomeFileOrDir') # upload file to IPFS & publish   
ipfs_api.update_ipns_record_from_hash('MyWebsite', cid) # publish IPFS content to IPNS key  

# IPFS PubSub  
ipfs_api.subscribe_to_topic("test", print) # print is the eventhandler  
ipfs_api.publish_to_topic("test", "Hello there!")
```
#### HTTP API access:
This allows you to access the official IPFS API (the same as the command line ipfs utility) through ipfshttpclients' `client` object. At this stage of development it is incomplete.

Examples:
```Python
import ipfs_api
ipfs_api.http_client.add("helloworld.txt")
ipfs_api.dht.findpeer("QMHash")
print(ipfs_api.swarm.peers())
```

## IPFS-Datatransmission
`import ipfs_datatransmission`

A Python module for limitless, easy, private peer-to-peer data transmission other over the IPFS Network.

This module has three main pairs functions for use by the user:
- __Simple Data Transmission:__
    - `transmit_data(data, peerID, listener_name)`
    - `listen_for_transmissions(listener_name,` eventhandler)
- __File Transmission:__
    - `transmit_file(data, peerID, listener_name)`
    - `listen_for_file_transmissions(listener_name, eventhandler)`
- __Conversations (Ping-Pong Data & File Transmission):__
    - `start_conversation(data, peerID, listener_name)`
    - `listen_for_conversations(listener_name, eventhandler)`

See the _Examples_ folder for the different ways of using these functions. They are designed in a way that makes them easy to use for simple applications but feature-rich for more demanding ones, such as encryption integration and access to low-level protocol settings.

### Listener Functions:
The listener functions (listen_for_transmissions, listen_for_file_transmissions and listen_for_conversations) produce Listener objects () that run on their own threads waiting for incoming data transmission or conversation requests. When another computer wants to send the first computer somthing, the other computer sends a transmission request which the Listener object receives and reacts to by creating a Transmission reception object () which runs on its own separate thread to receive the transmission, or in the case of the conversation listener, calls its user-defined eventhandler so that the conversation can be joined or ignored.
This system of receiving data transmissions/conversations allows a computer to receive multiple transmission addressed to the same listener simultaneously.
Multiple Listeners of the same type (the types being DataTransmission, FileTransmission, or Conversation) can be run simultaneously and independently, for example by different programs. Those different listeners (instances of listen_for_transmissions) must me named to distinguish them from each other for addressing purposes. This name is the "listener_name" parameter in the listener functions. The name is chosen by the user when creating the listener (e.g. when calling ListenForTransmission()), and must be provided when starting a transmission (e.g. when calling transmit_data()).

## IPFS-LNS:
`import ipfs_lns`

IPFS-LNS (IPFS Local Name System) allows you to store IPFS nodes' peer IDs and names in a database stored on your local machine. IPFS-LNS also stores a list of multiaddresses (essentially IP addresses) that the peer has been known to use, as long as you use IPFS-LNS to connect or check the connection to that peer. Every time you try to connect to the peer, IPFS-LNS tries to specifically connect to the peer using the known multiaddresses from previous connections, which can dramatically increase the speed of doing so compared to searching the whole IPFS network for the peer.


Basic usage:  
```python
import ipfs_api  

# check connection to peer of peerID "QmHash" and whom we call "Bob", add him to our list of known peers ("contacts") if he is not already added  
ipfs_api.check_peer_connection("QmHash", "Bob") 

import ipfs_lns
peerID = ipfs_lns.lookup_contact("Bob") # get the contact 'Bob's IPFS peer ID
```
# IPFS Technicalities:
How does IPFS-DataTransmission use IPFS to to send data to another computer? After all, IPFS is a file system and made for sharing and storing files, creating a content addressed internet. Does it really provide the functionality for two computers to communicate directly which each other?  
Yes, IPFS does provide that functionality, although as of November 2021 that is still an experimental feature. That's why you have to configure IPFS to enable that feature as described in Prerequisites.txt.  
After all, IPFS relies on peers sending data to each other over its decentralised network using a communication technology called libp2p. IPFS-DataTransmission essentially uses the libp2p module inside of the IPFS process running on the computer to communicate to other computers via an access point to the module which IPFS provides, the experimental feature which IPFS calls Libp2pStreamMounting. Libp2pStreamMounting works by allowing the user to set up a port forwarding system on the computer between the user's program (in this case IPFS-DataTransmission) and the libp2p process inside of IPFS. After setting up this port forwarding the user (in this case the IPFS-DataTransmission script) can communicate to the chosen local port on their computer, and IPFS forwards that communication to the libp2p module runnning inside of IPFS on the other computer, which forwards it in turn to a preconfigured port on that computer, to be listened to by the user (in this case an IPFS-DataTransmission Listener object).  
Because the Python API for interacting with IPFS (ipfshttpclient) doesn't yet support this experimental feature, I have updated the module myself, the result of which is the ipfshttpclient2 folder in this code project, which will remain part of this project until the changes are integrated into the official ipfshttpclient module.

# Links
This project's IPFS URL:  
[ipns://k2k4r8nismm5mmgrox2fci816xvj4l4cudnuc55gkfoealjuiaexbsup#IPFS-Toolkit](https://ipfs.io/ipns/k2k4r8nismm5mmgrox2fci816xvj4l4cudnuc55gkfoealjuiaexbsup#IPFS-Toolkit)
