import IPFS_DataTransmission as IPFS

#VM
peerID = "QmNk3UYD6uYzEyebwjkaQzA3jAFT5q7DcvSJ8uiJCBki7j"
def Handler(con, data):
    print(data)
con = IPFS.StartConversationAwait("test", peerID, "test", Handler)
con.Say("Hello".encode())
print("said")
