import IPFS_DataTransmission

def func(data, peer):
    print(data, peer)

IPFS_DataTransmission.ListenToBuffers(func , "test application")
