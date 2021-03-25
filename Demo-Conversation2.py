import IPFS_DataTransmission as IPFS

def handler(con, data):
    print(data)

IPFS.ListenForConversations("test", handler)
