import IPFS_DataTransmission


# Eventhandler to handle received data
def OnReceive(data, PeerID):
    print("Received data transmission!")

    try:
        print(data.decode("utf-8"))
    except:
        print("Received file")
        f = open("received", "wb")
        f.write(data)
        f.close()


# starting to listen for incoming data transmissions
IPFS_DataTransmission.ListenForTransmissions("test application", OnReceive)


# Stoping this program form closing immediately, so that the listener doesn't get closed
import time
while(True):
    time.sleep(1)
