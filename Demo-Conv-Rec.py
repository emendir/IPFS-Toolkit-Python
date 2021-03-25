import IPFS_DataTransmission as IPFS

def ConvHandler(conversation, peerID):
    print("new conversation")
    def hear(conversation, peerID=None):
        #conversation.Join()
        conversation.Say("Hi back".encode("utf-8"))
    return hear
conv_lis = IPFS.ConversationListener("general_listener", ConvHandler)

while True:
    import time
    sleep(1)
