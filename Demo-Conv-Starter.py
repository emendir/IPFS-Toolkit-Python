import IPFS_DataTransmission as IPFS

def hear(conversation, data, peerID):
    print(data.decode('utf-8'))

conv = IPFS.Conversation()
conv.StartAwait("test-con", "Qmcbjtfh5RfyFnrPk6uQ5EfhHzPQqPC1Vga7twguXSg2Pm", "general_listener", hear)
conv.Say("hello there".encode('utf-8'))
#conv.Start("test-con", "12D3KooWDk7EhH8yS5deVZWoEBLSr5LRYCFLtN2GkVDtqv5sn4d7", "general_listener", hear)
while True:
    import time
    time.sleep(1)
