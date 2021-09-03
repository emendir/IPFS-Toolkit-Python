import IPFS_DataTransmission as IPFS


peerID = "12D3KooWDTtukVdcjjiSkGQGUFtPVjYXY7RyJisTW59wFLst93zZ"
#VM
peerID = "QmNk3UYD6uYzEyebwjkaQzA3jAFT5q7DcvSJ8uiJCBki7j"

#Llearuin
peerID = "12D3KooWGKNuAQPyaYTDbeiWFN3S2SSTbxH74XCbJNdf7prG9qPE"

ft = IPFS.FileTransmitter("/home/ubuntu-vm/go-ipfs_v0.8.0_linux-amd64.tar.gz", peerID, "filelistener", "testmeadata".encode())


while True:
    import time
    time.sleep(1)
