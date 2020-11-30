This is a Python module that enables two users to transmit data of any length to each other over the IPFS Network.

Folder Contents:
IPFS_DataTransmission.py: the Python module that enables users to transmit data to each other over the IPFS Network
IPFS_API.py: a wrapper for the module ipfshttpclient2 that makes that module easier to use
ipfshttpclient2: a modified version of the ipfshttpclient moodule that includes the ipfs.p2p functions (which are not included in the stadard module, as of version 0.6.1)

Demo-Sender.py: a simple Python script that sends a message (or optionally a file) to another peer on the IPFS Network
Demo-Receiver.py: a simple Python script that receives data transmissions over the IPFS Network


How to use the Demo scripts:
0. Make sure you have installed and setup all the prerequisites in the Prerequisites Section below.
1. RunIPFS with the experimental "Libp2pStreamMounting" feature enabled on two computers.
2. Run Demo-Receiver.py on the one computer.
3. Open Demo-Sender.py on the other computer, paste the IPFS ID of the first computer into the so marked field, and run the script.
4. The first computer will display the sent message in the window of the running Demo-Receiver program.

Prerequisites:
To use the IPFS_DataTransmission, the following software must be installed on your computer:
- IPFS (Desktop or CLI, doesn't matter. I have tested this module with both, IPFS v0.6.0 & 0.7.0)
    https://docs.ipfs.io/install/
- Enable "Libp2pStreamMounting" in IPFS:
        Desktop Version: on the Settings tab, scroll down to "IPFS CONFIG" and change the line that reads:
            "Libp2pStreamMounting": false,
            to:
            "Libp2pStreamMounting": true,
            Click the "Save" button and restart IPFS.
        CLI Version: run:
            ipfs config --json Experimental.Libp2pStreamMounting true
- Python3, version 3.5 or above
    https://www.python.org/downloads/
- Pip for Python3:
    https://pip.pypa.io/en/stable/installing/
- install prerequisite Python modules:
    sudo apt install python3-distutils
    pip3 install setuptools
    pip3 install wheel
    pip3 install multiaddr




