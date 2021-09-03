import IPFS_DataTransmission

# Elborth
peerID = "Qmcbjtfh5RfyFnrPk6uQ5EfhHzPQqPC1Vga7twguXSg2Pm"

sender = IPFS_DataTransmission.BufferSender(peerID, "test application")

while(False):
    sender.SendBuffer("hello there".encode()*80)
    import time
    time.sleep(1)

sender.SendBuffer("hello there".encode()*100)
