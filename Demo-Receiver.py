import IPFS_DataTransmission


# Eventhandler to handle received data
def OnReceive(data, PeerID):
    try:
        print(data.decode("utf-8"))
    except:
        print(f"Received non-text data from {PeerID}, saved it as a file.")
        with open("test_r", "wb") as conff:
            conff.write(data)


# starting to listen for incoming data transmissions
IPFS_DataTransmission.ListenForTransmissions("test application", OnReceive)


# Stoping this program form closing immediately, so that the listener doesn't get closed
import time
while(True):
    time.sleep(1)
