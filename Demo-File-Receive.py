import IPFS_DataTransmission as IPFS

def OnDataReceived(peer, file, metadata):
    print(metadata)
    print(file)
    print(peer)
fr = IPFS.ListenForFileTransmissions("filelistener", OnDataReceived)
while(True):
    import time
time.sleep(1)
