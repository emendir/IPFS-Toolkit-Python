This is a Python module that enables two users to easily transmit data of any length to each other over the IPFS Network.

Folder Contents: --------------------------------
IPFS_DataTransmission.py: the Python module that enables users to transmit data to each other over the IPFS Network
- IPFS_API.py: a wrapper for the module ipfshttpclient2 that makes that module easier to use
- ipfshttpclient2: a modified version of the ipfshttpclient module that includes the ipfs.p2p functions (which are not included in the standard module, as of version 0.6.1)
- Demo-Sender.py: a simple Python script that sends a message (or optionally a file) to another peer on the IPFS Network
- Demo-Receiver.py: a simple Python script that receives data transmissions over the IPFS Network
- Prerequisites.txt: a set of instructions for installing and configuring all the prerequisite software tools needed for using this module (IPFS and Python)
- HowItWorks.txt: provides a conceptual overview of how this module works, explaining the understanding needed to use the module properly and giving some technical details about how this module uses IPFS


How to use the Demo scripts: --------------------
0. Make sure you have installed and setup all the prerequisites as described in Prerequisites.txt.
1. Run IPFS with the experimental "Libp2pStreamMounting" feature enabled on two computers.
2. Run Demo-Receiver.py on the one computer.
3. Open Demo-Sender.py on the other computer, paste the IPFS ID of the first computer into the so marked field, and run the script.
4. The first computer will display the sent message in the window of the running Demo-Receiver program.
