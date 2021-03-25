import IPFS_DataTransmission as IPFS


peerID = "12D3KooWDTtukVdcjjiSkGQGUFtPVjYXY7RyJisTW59wFLst93zZ"
#VM
peerID = "QmNk3UYD6uYzEyebwjkaQzA3jAFT5q7DcvSJ8uiJCBki7j"
ft = IPFS.FileTransmitter("/home/elborth/Music/Link to Music/Davy Jones  - Pirates of the Caribbean.mp3", peerID, "filelistener", "testmeadata".encode())


while True:
    import time
    time.sleep(1)
