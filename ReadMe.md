A library for working with IPFS in Python.  
It includes a programmer-friendly API called __ipfs_api__ for easy usage of some of the most useful IPFS features, a module called __ipfs_datatransmission__ that allows for easy direct P2P data transmission between two IPFS nodes and a module called __ipfs_lns__ for remembering the multiaddressess of known IPFS nodes ("contacts") to speed up connection times.

Under the hood these modules use a slightly updated version [ipfshttpclient](https://github.com/ipfs-shipyard/py-ipfs-http-client), a no-longer-maintained Python package for interacting with IPFS via its HTTP-API. The modified package can be accesses as ipfs_api.ipfshttpclient2 to gain full access to all supported ipfs interactivity in a structured manner similar to the IPFS CLI. In environments where interaction with the IPFS via HTTP is not possible, this package automatically uses __ipfs_cli__ as a fallback, a module that provides all the functionality of ipfs_api by communicating to ipfs via its command-line interface. 


# Package Contents:
## Python Modules:
- __ipfs_api__: a wrapper for the module ipfshttpclient2 that provides a simple API for some of the most useful features of IPFS
- __ipfs_datatransmission__: a module that enables P2P data transmission between IPFS nodes
- __ipfs_lns__: a module that allows IPFS nodes and their multiaddresses to be stored in app data to make them easier to find in the IP layer of the internet (easier to connect to)
- __ipfshttpclient2__: a modified version of the official ipfshttpclient module that has been expanded and updated where needed 

## Other:
- __Examples__: a folder of scripts demonstrating how to work with ipfs_datatransmission


# Development Updates: v0.5.0 is released!

This library is still under development and is currently being tested in various use-case projects. Due to its early stage of development, some successive versions of this library are not fully backward-compatible with their previous versions.  
A history of the changes made in all updates is kept under  [./ChangeLog.md](./ChangeLog.md). 
### Overview
- renamed all modules and functions from PascalCase to snake_case to conform with Python naming conventions
- massive speed improvements to the IPFS-DataTransmission protocol (not backward-compatible)

## Renaming
IPFS-Toolkit has finally adopted standard Python naming conventions! With version 0.5.0, all functions and class methods have been renamed from PascalCase to snake_case to comply with PEP8. The now deprecated PascalCase version of modules remain in v0.5.X so as not to immediately break applications on updating this library, albeit with annoying deprecation warnings in the console output to encourage programmers to take a few minutes and update their code. 
## IPFS-DataTransmission Protocol Updates (not backward-compatible)
With version 0.5.0, the underlying communication protocol on which all of the features of the ipfs_datatransmission module are built has been improved to bring a massive increase in the speed of connection establishment. Unfortunately, this update lacks backward compatibility, which means that if you have built a project that uses ipfs_datatransmission, instances of your program running v0.4.X and v0.5.X of IPFS-Toolkit won't be able to communicate with each other.
## Other
- Documentation: full API reference for ipfs_api and ipfs_datatransmission in [./Documentation](./Documentation) 
- various minor feature updates, see [./ChangeLog.md](./ChangeLog.md) 


# Getting started with IPFS-Toolkit:
1. Install IPFS-Toolkit (see below)
2. Read the _Modules Contained in IPFS-Toolkit_ section below to learn what this package contains and how it works. For details about the functions contained in the modules, check out the API reference in [./Documentation](./Documentation) 
3. For IPFS-DataTransmission: Read and try out the demo scripts in the Examples folder.

## Setup
### Installation
`pip install IPFS-Toolkit`



### Prerequisites
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
  (depending on your Python installation you may need to use `pip` instead of `pip3` in the following commands)  
```bash
pip3 install appdirs httpcore httpx idna multiaddr setuptools wheel zmq
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
ipfs_api.update_ipns_record_from_cid('MyWebsite', cid) # publish IPFS content to IPNS key  

# IPFS PubSub  
ipfs_api.pubsub_subscribe("test", print) # print is the eventhandler  
ipfs_api.pubsub_publish("test", "Hello there!")
```
#### HTTP API access:
This allows you to almost full access the IPFS API through a naming structure similar to its CLI through ipfshttpclient's `client` object. At this stage of development it is incomplete.

Examples:
```Python
import ipfs_api
ipfs_api.http_client.add("helloworld.txt")
ipfs_api.http_client.routing.findpeer("QMHash")
ipfs_api.http_client.swarm.peers()
```

To check and somewhat manage the status of the IPFS daemon, see [Examples/Demo-Check-IPFS-Status.py](Examples/Demo-Check-IPFS-Status.py)

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
The listener functions (listen_for_transmissions, listen_for_file_transmissions, and listen_for_conversations) produce Listener objects () that run on their own threads waiting for incoming data transmission or conversation requests. When another computer wants to send the first computer something, the other computer sends a transmission request which the Listener object receives and reacts to by creating a Transmission reception object () which runs on its own separate thread to receive the transmission, or in the case of the conversation listener, calls its user-defined eventhandler so that the conversation can be joined or ignored.
This system of receiving data transmissions/conversations allows a computer to receive multiple transmissions addressed to the same listener simultaneously.
Multiple Listeners of the same type (the types being DataTransmission, FileTransmission, or Conversation) can be run simultaneously and independently, for example by different programs. Those different listeners (instances of listen_for_transmissions) must be named to distinguish them from each other for addressing purposes. This name is the "listener_name" parameter in the listener functions. The name is chosen by the user when creating the listener (e.g. when calling ListenForTransmission()) and must be provided when starting a transmission (e.g. when calling transmit_data()).

## IPFS-LNS:
`import ipfs_lns`

IPFS-LNS (IPFS Local Name System) allows you to store IPFS nodes' peer IDs and names in a database stored on your local machine. IPFS-LNS also stores a list of multiaddresses (essentially IP addresses) that the peer has been known to use, as long as you use IPFS-LNS to connect or check the connection to that peer. Every time you try to connect to the peer, IPFS-LNS tries to specifically connect to the peer using the known multiaddresses from previous connections, which can dramatically increase the speed of doing so compared to searching the whole IPFS network for the peer.


Basic usage:  
```python
import ipfs_api  

# check the connection to the peer of peerID "QmHash" and whom we call "Bob", add him to our list of known peers ("contacts") if he is not already added  
ipfs_api.check_peer_connection("QmHash", "Bob") 

import ipfs_lns
peerID = ipfs_lns.lookup_contact("Bob") # get the contact 'Bob's IPFS peer ID
```
# IPFS Technicalities:
How does IPFS-DataTransmission use IPFS to send data to another computer? After all, IPFS is a file system made for sharing and storing files, creating a content addressed internet. Does it really provide the functionality for two computers to communicate directly with each other?  
Yes, IPFS does provide that functionality, although as of November 2021 that is still an experimental feature. That's why you have to configure IPFS to enable that feature as described in Prerequisites.txt.  
After all, IPFS relies on peers sending data to each other over its decentralized network using a communication technology called libp2p. IPFS-DataTransmission essentially uses the libp2p module inside of the IPFS process running on the computer to communicate to other computers via an access point to the module that IPFS provides, the experimental feature that IPFS calls Libp2pStreamMounting. Libp2pStreamMounting works by allowing the user to set up a port forwarding system on the computer between the user's program (in this case IPFS-DataTransmission) and the libp2p process inside of IPFS. After setting up this port forwarding the user (in this case the IPFS-DataTransmission script) can communicate to the chosen local port on their computer, and IPFS forwards that communication to the libp2p module running inside of IPFS on the other computer, which forwards it in turn to a preconfigured port on that computer, to be listened to by the user (in this case an IPFS-DataTransmission Listener object).  
Because the Python API for interacting with IPFS (ipfshttpclient) doesn't yet support this experimental feature, I have updated the module myself, the result of which is the ipfshttpclient2 folder in this code project, which will remain part of this project until the changes are integrated into the official ipfshttpclient module.

# Links
This project's IPFS URL:  
[ipns://k2k4r8nismm5mmgrox2fci816xvj4l4cudnuc55gkfoealjuiaexbsup#IPFS-Toolkit](https://ipfs.io/ipns/k2k4r8nismm5mmgrox2fci816xvj4l4cudnuc55gkfoealjuiaexbsup#IPFS-Toolkit)
